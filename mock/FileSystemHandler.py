import pathlib
from typing import Union, Dict, Any, List

from fastapi_jwt_auth import AuthJWT

from .db import Session, ObjectType, UserData, get_user_id, get_first_of, insert_item, update_item, delete_item
from .exceptions import HTTP404Error


class FSHandler:
    fs = pathlib.Path("fs")

    session: Union[Session, None]
    user_id: str

    def __init__(self, auth: Union[AuthJWT, int], session: Union[Session, None] = None):
        self.session = session

        if isinstance(auth, AuthJWT):
            auth = str(get_user_id(auth))

        self.user_id = auth

    # WRITE
    def write_internal_object(self, object_type: str, content: str) -> str:
        assert object_type in ("clientsettings", "keystore")

        path = self.fs / self.user_id / object_type
        with open(path, "r", encoding = "utf-8") as f:
            f.write(content)

        return content

    def write_object(self, object_type: ObjectType, object_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        path = self.fs / self.user_id / object_type
        path.mkdir(exist_ok = True)
        path /= object_id

        data: str = content.pop("data")
        user_data = insert_item(self.session, UserData(**content))

        with open(path, "w", encoding = "utf-8") as f:
            f.write(data)

        return {**user_data.dict(), "data": data}

    # READ
    def read_internal_object(self, object_type: str) -> Union[None, str]:
        assert object_type in ("clientsettings", "keystore")

        path = self.fs / self.user_id / object_type
        if not path.is_file():
            return None

        with open(path, "r", encoding = "utf-8") as f:
            return f.read()

    def read_object_from_path(self, path: pathlib.Path, object_type: ObjectType, object_id: str) -> Dict[str, Any]:
        user_data = get_first_of(self.session, UserData, UserData.type == object_type and UserData.id == object_id)
        if user_data is None:
            raise HTTP404Error("Specified object was not found.")

        with open(path, "r", encoding = "utf-8") as f:
            data = f.read()

        return {**user_data.dict(), "data": data}

    def get_path(self, object_type: ObjectType, object_id: str) -> pathlib.Path:
        path = self.fs / self.user_id / object_type
        if not path.is_dir():
            raise HTTP404Error("Specified object was not found.")

        path /= object_id
        if not path.is_file():
            raise HTTP404Error("Specified object was not found.")

        return path

    def read_objects(self, object_type: ObjectType) -> List[Dict[str, Any]]:
        path = self.fs / self.user_id / object_type
        if not path.is_dir():
            return []

        return [self.read_object_from_path(p, object_type, p.stem) for p in path.iterdir()]

    def read_object(self, object_type: ObjectType, object_id: str) -> Dict[str, Any]:
        path = self.get_path(object_type, object_id)

        return self.read_object_from_path(path, object_type, object_id)

    # PATCH
    def patch_object(self, object_type: ObjectType, object_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        path = self.get_path(object_type, object_id)

        data: str = content.pop("data")

        user_data = update_item(
            self.session,
            UserData,
            UserData.type == object_type and UserData.id == object_id,
            **content
        )
        if user_data is None:
            raise HTTP404Error("Specified object was not found.")

        with open(path, "w", encoding = "utf-8") as f:
            f.write(data)

        return {**user_data.dict(), "data": data}

    # DELETE
    def delete_object(self, object_type: ObjectType, object_id: str) -> Dict[str, Any]:
        path = self.get_path(object_type, object_id)

        user_data = delete_item(self.session, UserData, UserData.type == object_type and UserData.id == object_id)
        if user_data is None:
            raise HTTP404Error("Specified object was not found.")

        with open(path, "r", encoding = "utf-8") as f:
            data = f.read()

        path.unlink()

        return {**user_data.dict(), "data": data}

    def delete_all(self):
        path = self.fs / self.user_id
        path.unlink(missing_ok = True)
