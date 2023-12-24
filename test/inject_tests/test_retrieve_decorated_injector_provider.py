import os.path
import unittest

import injector

from python_di.inject.context_builder.component_scanner import ComponentScanner
from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs


class TestDecorate(unittest.TestCase):
    def test_scanner_retrieve_configuration_clzz(self):
        from python_di.inject.context_builder.injection_context import InjectionContext
        inject_ctx = InjectionContext()
        ctx = inject_ctx.initialize_env()
        component_scanner: ComponentScanner = ctx.get_interface(ComponentScanner, scope=injector.singleton)

        assert component_scanner is not None

        starting = os.path.dirname(os.path.dirname(__file__))
        configs = component_scanner._retrieve_decorated(
            InjectionContextInjectorContextArgs(inject_ctx.ctx, {starting}, os.path.dirname(starting)),
            "configuration")

        assert len(configs) != 0
        assert len(configs) == 3
        assert all([hasattr(c, 'context_factory') for c in configs])


if __name__ == '__main__':
    unittest.main()
