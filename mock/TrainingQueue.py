from collections import deque
from threading import Lock
from time import sleep
from typing import Set, Deque

from .models import AiModuleDto
from .db import Session, Status, insert_item, update_item


class TrainingQueue:
    SECS_PER_STEP = 0.1

    _users_in_queue: Set[str]
    _queue: Deque[AiModuleDto]
    _lock: Lock

    session: Session

    def __init__(self, session: Session):
        self._lock = Lock()
        self._users_in_queue = set()
        self._queue = deque()

        self.session = session

    def add_module(self, module: AiModuleDto) -> bool:
        if module.user_id in self._users_in_queue:
            raise

        with self._lock:
            self._users_in_queue.add(module.user_id)
            self._queue.append(module)
            module = insert_item(self.session, module)
            assert module is not None

        return True

    def run(self):
        while True:
            with self._lock:
                module = self._queue.popleft() if len(self._queue) else None

            # poll every 5 secs
            if module is None:
                sleep(5)
                continue

            module: AiModuleDto = update_item(self.session, module, status = Status.training)
            assert module is not None

            sleep(module.steps * self.SECS_PER_STEP)

            module: AiModuleDto = update_item(self.session, module, status = Status.ready)
            assert module is not None
