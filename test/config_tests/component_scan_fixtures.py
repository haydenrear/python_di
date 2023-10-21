import injector

from config_tests.component_scan_fixture import TestOne, TestTwo
from config_tests.other_component_scan_fixture import TestOneHundred
from python_di.configs.autowire import autowired, injectable, post_construct
from python_di.configs.component import component
from python_di.inject.prototype import prototype_scope, prototype_factory


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


@prototype_scope
class TestPrototypeScopeComponentOne:

    @prototype_factory()
    def __init__(self, test: TestTwo):
        self.test = test


@prototype_scope
class TestPrototypeScopeComponentTwo:
    @prototype_factory()
    def __init__(self, test: TestTwo, other_component: TestPrototypeScopeComponentOne):
        self.other_component = other_component
        self.test = test


@prototype_scope
class TestPrototypeScopeComponentThree:
    @prototype_factory()
    def __init__(self, test: TestTwo, other_component: TestPrototypeScopeComponentOne,
                 value: str = 'hello'):
        self.value = value
        self.other_component = other_component
        self.test = test


@prototype_scope
class TestPrototypeScopeComponentFour:
    @prototype_factory(dep_bean_profiles={'test_one_hundred': 'test'})
    def __init__(self, test: TestTwo, other_component: TestPrototypeScopeComponentOne,
                 test_one_hundred: TestOneHundred, value: str = 'hello'):
        self.test_one_hundred = test_one_hundred
        self.value = value
        self.other_component = other_component
        self.test = test


@prototype_scope
class TestPrototypeScopeComponentFive:
    @prototype_factory(dep_bean_profiles={'test_one_hundred': 'prod'})
    def __init__(self, test: TestTwo, other_component: TestPrototypeScopeComponentOne,
                 test_one_hundred: TestOneHundred, value: str = 'hello'):
        self.test_one_hundred = test_one_hundred
        self.value = value
        self.other_component = other_component
        self.test = test
