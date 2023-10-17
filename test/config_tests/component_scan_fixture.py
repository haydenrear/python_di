import dataclasses

import injector
from injector import Binder

from config_tests.test_component_scan_fixture import TestOne
from python_di.configs.component import component


class TestBean:
    def __init__(self, special):
        self.special = special


class Config(injector.Module):

    def configure(self, binder: Binder) -> None:
        binder.bind(TestBean, TestBean('hello world!'), scope=injector.singleton)


class TestThree:
    pass


@component(bind_to=[TestThree, TestOne])
class TestOne(TestThree):
    pass


@dataclasses.dataclass(init=True)
class TestTwo:
    test_one: TestOne
