import dataclasses
import logging
import unittest

import injector

from config_tests.component_scan_fixture import TestBean, TestOne, TestTwo
from config_tests.component_scan_fixtures import TestAutowired, TestProfileInjection, \
    TestInjectionHasValue
from config_tests.other_component_scan_fixture import TestOneHundred
from python_di.configs.autowire import component
from python_di.configs.di_configuration import get_config_clzz, configuration, enable_configuration_properties, \
    component_scan, bean, lazy
from python_di.inject.prioritized_injectors import SingletonBindingExistedException
from python_di.inject.composite_injector import ProfileScope, CompositeScope
from python_di.inject.injector_provider import InjectionContext
from python_util.logger.log_level import LogLevel
from python_di.reflect_scanner.file_parser import FileParser
from python_di.reflect_scanner.graph_scanner import DecoratorOfGraphScanner, DecoratorOfGraphScannerArgs
from python_di.reflect_scanner.module_graph_models import GraphType
from python_di.reflect_scanner.program_parser import ScannerProperties
from test_framework.assertions.assert_all import assert_all


@dataclasses.dataclass(init=True)
class TestFive:
    test_one: TestOne


@configuration(profile='test')
@enable_configuration_properties(config_props=[ScannerProperties])
@component_scan(base_packages=['config_tests.component_scan_fixture', "config_tests.other_component_scan_fixture"])
class TestComponentScan:

    @lazy
    @bean()
    def value_two(self, one: TestOne) -> TestTwo:
        self.three = one
        return TestTwo(self.three)

    @bean()
    @lazy
    def value_three(self, one: TestOne) -> TestFive:
        self.four = one
        out_test = TestFive(self.four)
        return out_test


class TestSelfBeanFactoryBean:
    def __init__(self, test: TestOne, test_one_hundred: TestOneHundred):
        self.test_one_hundred = test_one_hundred
        self.test = test


@component()
class TestSelfBeanFactory:

    @bean(profile='test', self_factory=True, scope=ProfileScope)
    @lazy
    def test_self_bean_factory(self, test: TestOne, test_one_hundred: TestOneHundred):
        return TestSelfBeanFactoryBean(test, test_one_hundred)


class ComponentScanTest(unittest.TestCase):

    def setUp(self):
        LogLevel.set_log_level(logging.DEBUG)
        self.component_scan_config: TestComponentScan \
            = InjectionContext.get_interface(get_config_clzz(TestComponentScan))
        self.two = InjectionContext.get_interface(TestTwo)
        self.three = InjectionContext.get_interface(TestFive)

        assert self.component_scan_config is not None
        assert self.two is not None
        assert self.three is not None

    def test_self_bean_factory(self):
        test_self_bean_f = InjectionContext.get_interface(TestSelfBeanFactoryBean)
        test_one_hundred = InjectionContext.get_interface(TestOneHundred, profile='test')
        asserter = assert_all()
        asserter(test_self_bean_f is not None, "Test self bean factory was None")
        asserter(test_self_bean_f.test is not None, "Internal test was none")
        asserted = asserter(test_self_bean_f.test_one_hundred == test_one_hundred,
                            "Test one hundred was not correct profile.")
        asserted()

    def test_inject_from_profile_scope_into_singleton_scope(self):
        from config_tests.other_component_scan_fixture import TestOneHundred
        out = InjectionContext.get_interface(TestOneHundred, profile='prod',
                                             scope=injector.ScopeDecorator(ProfileScope))
        assert out.test_value == "special_val"
        out = InjectionContext.get_interface(TestOneHundred, profile='test',
                                             scope=injector.ScopeDecorator(ProfileScope))
        assert out.test_value == "special_test_val"
        # assert that different profiles inject dependencies from those profiles.

        InjectionContext.register_component(TestProfileInjection, [TestProfileInjection],
                                            scope=injector.ScopeDecorator(ProfileScope), profile='test')
        InjectionContext.register_component(TestProfileInjection, [TestProfileInjection],
                                            scope=injector.ScopeDecorator(ProfileScope), profile='prod')
        out = InjectionContext.get_interface(TestProfileInjection, scope=injector.ScopeDecorator(ProfileScope),
                                             profile='prod')

        assert out.test_one_hundred.test_value == 'special_val'
        out = InjectionContext.get_interface(TestProfileInjection, scope=injector.ScopeDecorator(ProfileScope),
                                             profile='test')
        assert out.test_one_hundred.test_value == 'special_test_val'
        # assert that the dependency used as the singleton is that which has highest precedence.

        out = InjectionContext.get_interface(TestProfileInjection, scope=injector.singleton)
        assert out.test_one_hundred.test_value == 'special_val'
        out = InjectionContext.get_interface(CompositeScope, scope=injector.singleton)
        assert TestProfileInjection not in out

        self.assertRaises(SingletonBindingExistedException, lambda: InjectionContext.register_component_value(
            [TestProfileInjection],
            TestProfileInjection(TestOneHundred("again_test")),
            scope=injector.singleton))
        self.assertRaises(SingletonBindingExistedException, lambda: InjectionContext.register_component(
            TestProfileInjection,
            [TestProfileInjection],
            scope=injector.singleton))

    def test_inject_singleton_scope_into_profile_scope(self):
        InjectionContext.register_component(TestInjectionHasValue, [TestInjectionHasValue],
                                            scope=injector.ScopeDecorator(ProfileScope), profile='test')
        out = InjectionContext.get_interface(TestInjectionHasValue)
        assert out is not None
        assert out.test == InjectionContext.get_interface(TestTwo)

    def test_component_scan_configuration_annot(self):
        from config_tests.other_component_scan_fixture import TestOneHundred
        out = InjectionContext.get_interface(TestOneHundred, profile='prod',
                                             scope=injector.ScopeDecorator(ProfileScope))
        assert out.test_value == "special_val"
        out = InjectionContext.get_interface(TestOneHundred, profile='test',
                                             scope=injector.ScopeDecorator(ProfileScope))
        assert out.test_value == "special_test_val"
        out = InjectionContext.get_interface(TestOneHundred, profile='prod')
        assert out.test_value == "special_val"
        out = InjectionContext.get_interface(TestOneHundred, scope=injector.singleton)
        assert out.test_value == "special_val"

    def test_config_props(self):
        scanner = InjectionContext.get_interface(ScannerProperties)
        assert scanner is not None

    def test_autowired(self):
        autowired_bean = InjectionContext.get_interface(TestAutowired)
        assert autowired_bean.yes == 'hello'
        assert autowired_bean.one is not None

    def test_component_scan_component_test(self):
        t = InjectionContext.get_interface(TestOne)
        assert issubclass(type(t), TestOne)

    def test_configs(self):
        t = InjectionContext.get_interface(TestOne)
        two = InjectionContext.get_interface(TestFive)
        four = InjectionContext.get_interface(TestTwo)
        configs_three = self.component_scan_config.three
        configs_four = self.component_scan_config.four
        assert four is not None
        assert configs_four is not None
        assert configs_three is not None
        assert configs_three == configs_four
        assert t == two.test_one == configs_three == configs_four, f"{t}, {two.test_one}, {configs_four}, {configs_three}"

    def test_beans(self):
        three_from_i = InjectionContext.get_interface(TestFive)
        assert three_from_i.test_one == self.component_scan_config.four

    def test_injection(self):
        first = InjectionContext.get_interface(FileParser, profile='main_profile', scope=injector.noscope)
        second = InjectionContext.get_interface(FileParser, profile='main_profile', scope=injector.noscope)

        assert len(first.graph) == 0
        assert len(second.graph) == 0

        assertions = assert_all()
        assertions(first != second, "Injector for file parser needed no scope, not singleton, because different graph "
                                    "needs to be created for each file.")
        assertions(all([first.parsers[i] == second.parsers[i] for i in range(len(first.parsers))]),
                   "File parsers need to have same injections.")

        parsed = first.parse(__file__)
        parser = InjectionContext.get_interface(DecoratorOfGraphScanner)

        out = parser.do_scan(DecoratorOfGraphScannerArgs("configuration", parsed, GraphType.File))
        next_out = parser.do_scan(
            DecoratorOfGraphScannerArgs("enable_configuration_properties", parsed, GraphType.File))

        assertions(len(set(out.nodes)) == 1,
                   f"{', '.join([str(n) for n in out.nodes])} are the nodes, of which there are {len(out.nodes)}.")

        assertions('TestComponentScan' in [i.id_value for i in out.nodes],
                   'TestComponentScan was not provided by FileParser.')

        assertions(len(set(next_out.nodes)) == 1,
                   f"{', '.join([str(n) for n in out.nodes])} are the nodes, of which there are {len(out.nodes)}.")

        asserted = assertions('TestComponentScan' in [i.id_value for i in next_out.nodes],
                              'TestComponentScan was not provided by FileParser.')
        asserted()

    def test_component_scan(self):
        out: TestBean = InjectionContext.get_interface(TestBean)
        assert out.special == 'hello world!'
