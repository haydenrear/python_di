import dataclasses

from python_di.configs.di_configuration import configuration, lazy, bean
from python_di.inject.composite_injector import ProfileScope


@dataclasses.dataclass(init=True)
class TestOneHundred:
    test_value: str


@configuration(profile="test")
class TestConfigHundred:

    @lazy
    @bean(profile='prod', scope=ProfileScope)
    def value_two(self) -> TestOneHundred:
        return TestOneHundred("special_val")

    @lazy
    @bean(profile='test', scope=ProfileScope)
    def value_two_other(self) -> TestOneHundred:
        return TestOneHundred("special_test_val")
