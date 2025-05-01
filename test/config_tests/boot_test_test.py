import unittest

from config_tests.fixtures.to_inject_component import ToInjectComponent
from config_tests.tst_booter import TestBoot
from python_di.configs.test import boot_test
from python_di.configs.bean import test_inject
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


@boot_test(ctx=TestBoot)
class BootTestTest(unittest.TestCase):
    to_inject: ToInjectComponent

    @test_inject()
    @autowire_fn()
    def construct(self, to_inject: ToInjectComponent):
        BootTestTest.to_inject = to_inject

    def test_boot_test(self):
        assert self.to_inject is not None
