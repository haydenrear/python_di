from typing import Optional


class TestStr:
    def __init__(self, one: str):
        self.one = one


class TestOptional:
    def __init__(self, opt: Optional[str]):
        self.opt = opt


class TestDict:
    def __init__(self, dct: dict[str, str]):
        self.dct = dct


class TestDictOfList:
    def __init__(self, dct: dict[str, list[str]]):
        self.dct = dct


class TestList:
    def __init__(self, lst: list[str]):
        self.lst = lst


class TestAgg:
    def __init__(self, dct: dict[str, TestStr], lst: list[TestStr]):
        self.dct = dct
        self.lst = lst
