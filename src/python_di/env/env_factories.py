import typing
from typing import Optional

from pydantic import BaseModel


class Factory(BaseModel):
    factory: str
    lazy: bool

class Factories(BaseModel):
    factories: typing.List[Factory]
