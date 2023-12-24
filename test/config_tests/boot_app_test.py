import unittest

from config_tests.fixtures.to_inject_component import ToInjectComponent
from python_di.configs.app import boot_application
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


class BootAppTest(unittest.TestCase):

    def test_boot_app(self):
        @boot_application()
        class TestBootApp:
            pass

        value = self.autowire_value()
        assert value is not None
        assert value.c is not None

    @autowire_fn()
    def autowire_value(self, to_inject: ToInjectComponent) -> ToInjectComponent:
        return to_inject