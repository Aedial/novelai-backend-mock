from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from typing import Dict, Optional


# HTTP
class HTTPExceptionBase(HTTPException):
    STATUS_CODE = 0
    DEFAULT_MSG = ""

    def __init__(self, msg: str = DEFAULT_MSG):
        super().__init__(self.STATUS_CODE, detail = msg)


class HTTP400Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_400_BAD_REQUEST
    DEFAULT_MSG = "A validation error occured."


class HTTP401Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DEFAULT_MSG = "Access Token is incorrect."


class HTTP402Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_402_PAYMENT_REQUIRED
    DEFAULT_MSG = "An active subscription is required to access this endpoint."


# TODO: add 403 msg
class HTTP403Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_403_FORBIDDEN
    DEFAULT_MSG = ""


class HTTP404Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_404_NOT_FOUND
    DEFAULT_MSG = "Specified object was not found."


class HTTP409Error(HTTPExceptionBase):
    STATUS_CODE = status.HTTP_409_CONFLICT
    DEFAULT_MSG = "A conflict error occured."


# JSON
class JSONResponseBase(JSONResponse, Exception):
    STATUS_CODE = 0

    def __init__(self, content: Optional[Dict] = None):
        if content is None:
            content = {}

        super().__init__(content, self.STATUS_CODE)


class JSON409Error(JSONResponseBase):
    STATUS_CODE = status.HTTP_409_CONFLICT
