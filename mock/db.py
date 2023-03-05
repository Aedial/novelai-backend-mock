import json
from enum import Enum
from typing import Any, Union, List, Type, TypeVar, Optional
from uuid import UUID, uuid4

from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from sqlalchemy import Dialect, create_engine, select, insert, update, delete, literal_column, \
    Column, Text, Integer, Numeric, String, ForeignKey, Boolean, Enum as SQLEnum, DateTime, PickleType
from sqlalchemy.sql.type_api import _T
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import declarative_base, sessionmaker

from .exceptions import HTTP401Error, HTTP404Error


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    echo = True,
    future = True,
    connect_args={"check_same_thread": False}
)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# declarative base class
Base = declarative_base()


T = TypeVar("T")
ModelT = TypeVar("ModelT", bound = Union[Base, BaseModel])


def get_uuid4():
    uuid = uuid4()
    while uuid < 2 ** 31:
        uuid = uuid4()

    return uuid


class Array(TypeDecorator):
    impl = String

    @property
    def python_type(self) -> Type[Any]:
        return list

    def process_literal_param(self, value: Optional[_T], dialect: Dialect) -> str:
        pass

    def process_bind_param(self, value, dialect) -> Union[str, None]:
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect) -> Union[list, None]:
        if value is not None:
            value = json.loads(value)

        return value


class SubscriptionTier(int, Enum):
    NONE = 0
    TABLET = 1
    SCROLL = 2
    OPUS = 3


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    access_key = Column(String(64), unique = True, index = True)
    email = Column(String, unique = True, index = True)

    emailVerified = Column(Boolean)
    accountCreatedAt = Column(DateTime)

    tier = Column(SQLEnum(SubscriptionTier))
    active = Column(Boolean)
    expiresAt = Column(Numeric)
    maxPriorityActions = Column(Numeric)
    fixedTrainingStepsLeft = Column(Integer)
    purchasedTrainingSteps = Column(Integer)
    paymentProcessorData = Column(PickleType)


class ObjectType(str, Enum):
    STORY = "stories"
    STORYCONTENT = "storycontent"
    PRESET = "presets"
    MODULE = "aimodules"
    SHELF = "shelves"


class UserData(Base):
    __tablename__ = "user_data"

    id = Column(String, default = get_uuid4, primary_key=True)
    type = Column(String(16), primary_key=True)

    meta = Column(String(128))
    lastUpdatedAt = Column(Numeric)
    changeIndex = Column(Integer)


class GiftKey(Base):
    __tablename__ = "giftkey"

    id = Column(String, default = get_uuid4, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))

    model = Column(SQLEnum(SubscriptionTier))
    used = Column(Boolean)


class UserSubmission(Base):
    __tablename__ = "user_submission"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))

    dataName = String(256)
    authorName = String(256)
    authorEmail = String(256)
    socials = String(4096)
    mediums = String(4096)
    event = String(256)


class UserSubmissionVote(Base):
    __tablename__ = "user_submission_vote"

    user_id = Column(Integer, ForeignKey("user.id"), primary_key = True)
    event = Column(String(256), primary_key = True)

    submission_id = Column(Integer, ForeignKey("user_submission.id"))


class Model(str, Enum):
    field_2_7B = "2.7B"
    field_6B_v4 = "6B-v4"
    euterpe_v2 = "euterpe-v2"
    genji_python_6b = "genji-python-6b"
    genji_jp_6b = "genji-jp-6b"
    genji_jp_6b_v2 = "genji-jp-6b-v2"
    krake_v2 = "krake-v2"
    hypebot = "hypebot"
    infillmodel = "infillmodel"


class Status(str, Enum):
    pending = "pending"
    training = "training"
    ready = "ready"
    error = "error"


class AiModule(Base):
    __tablename__ = "ai_module"

    id = Column(String, default = get_uuid4, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))

    data = Column(String)
    lr = Column(Numeric)
    steps = Column(Integer)
    model = Column(SQLEnum(Model))
    lastUpdatedAt = Column(Numeric)
    status = Column(SQLEnum(Status))
    lossHistory = Column(Array)
    name = String(64)
    description = String(256)


class AccountVerification(Base):
    __tablename__ = "account_verification"

    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))


class AccountRecovery(Base):
    __tablename__ = "account_recovery"

    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))


class AccountDeletion(Base):
    __tablename__ = "account_deletion"

    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))


def get_session():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def get_user_id(auth: AuthJWT) -> int:
    auth.jwt_required()
    return auth.get_jwt_subject()


def add_commit_refresh(session: Session, item: Base):
    session.add(item)
    session.commit()
    session.refresh(item)


def insert_item(session: Session, item: ModelT) -> ModelT:
    model = item.__class__
    q = insert(model).values(**item.dict())
    return session.execute(q).scalars().one()


def update_item(session: Session, model: Type[ModelT], *conds: bool, **kwargs) -> ModelT:
    q = update(model).where(*conds).values(**kwargs)
    return session.execute(q).scalars().one()


def delete_item(session: Session, model: Type[ModelT], *conds: bool) -> ModelT:
    q = delete(model).where(*conds)
    return session.execute(q).scalars().one()


def get_first_of(session: Session, model: Type[ModelT], *conds: bool) -> Union[None, ModelT]:
    q = select(model).where(*conds)
    return session.execute(q).scalars().first()


def get_multiple_of(
    session: Session,
    model: Type[ModelT],
    *conds: bool,
    offset: int = 0,
    limit: Optional[int] = None
) -> List[T]:
    q = select(model).where(*conds).offset(offset).limit(limit)
    return session.execute(q).scalars().all()


def verify_exist_with(session: Session, *conds: bool, raise_if_not_exist: bool = True) -> bool:
    q = select(literal_column("1")).where(*conds)
    item = session.execute().scalar(q)
    if raise_if_not_exist and item is None:
        raise HTTP404Error()

    return item is not None


def verify_exist(
    session: Session,
    model: Type[ModelT],
    item_id: Union[UUID, int],
    raise_if_not_exist: bool = True,
) -> bool:
    return verify_exist_with(session, model.id == item_id, raise_if_not_exist = raise_if_not_exist)


def verify_exist_from_user(
    session: Session,
    model: Type[ModelT],
    user_id: Union[UUID, int],
    raise_if_not_exist: bool = True,
) -> bool:
    return verify_exist_with(session, model.user_id == user_id, raise_if_not_exist = raise_if_not_exist)


def count(
    session: Session,
    *conds: bool,
) -> int:
    q = select(literal_column("1")).where(*conds)
    return len(session.execute(q).scalars())


def get_user(auth: AuthJWT, session: Session, raise_if_not_exist: bool = True) -> Union[None, User]:
    user_id = get_user_id(auth)

    user = get_first_of(session, User, User.id == user_id)
    if user is not None:
        return user

    if raise_if_not_exist:
        raise HTTP401Error()

    return None
