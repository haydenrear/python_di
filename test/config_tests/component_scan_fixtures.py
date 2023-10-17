import injector

from config_tests.component_scan_fixture import TestOne, TestTwo
from python_di.configs.autowire import autowired, injectable, post_construct
from python_di.configs.component import component


class TestAutowiredBaseOne:
    pass


class TestAutowiredBaseTwo:
    pass


@component(bind_to=[TestAutowiredBaseOne, TestAutowiredBaseTwo])
@autowired(profile='test')
class TestAutowired:

    @injectable()
    def construct(self, one: TestOne):
        self.one = one
        assert self.one is not None

    @post_construct
    def post(self):
        self.yes = 'hello'


class TestProfileInjection:
    from config_tests.other_component_scan_fixture import TestOneHundred
    @injector.inject
    def __init__(self, test_one_hundred: TestOneHundred):
        self.test_one_hundred = test_one_hundred


class TestInjectionHasValue:
    @injector.inject
    def __init__(self, test: TestTwo):
        self.test = test
