import dataclasses

from python_di.configs.di_configuration import configuration, lazy, bean
from python_di.inject.composite_injector import ProfileScope, profile_scope, composite_scope


@dataclasses.dataclass(init=True)
class TestOneHundred:
    test_value: str


@configuration()
class TestConfigHundred:

    @lazy
    @bean()
    def value_two_other_main(self) -> TestOneHundred:
        return TestOneHundred("special_val_main")

    @lazy
    @bean(profile='test', scope=profile_scope)
    def value_two_other(self) -> TestOneHundred:
        return TestOneHundred("special_test_val")

    @lazy
    @bean(profile='prod', scope=profile_scope)
    def value_two(self) -> TestOneHundred:
        return TestOneHundred("special_val")
