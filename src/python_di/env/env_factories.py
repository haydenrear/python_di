import typing
from typing import Optional

from pydantic import BaseModel


class Factory(BaseModel):
    factory: str
    lazy: bool

class Factories(BaseModel):
    factories: typing.List[Factory]

    def get_factory(self, name: str) -> typing.Optional[Factory]:
        for f in self.factories:
            if f.factory == name:
                return f
