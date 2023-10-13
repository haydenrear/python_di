from typing import Optional

from pydantic import BaseModel


class Factory(BaseModel):
    factory: str
    lazy: bool
    priority: Optional[int] = -100


class Factories(BaseModel):
    factories: dict[str, list[Factory]]
