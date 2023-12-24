import os.path
import unittest

import torch.nn

from inject_tests.fixtures.component_scan_fixture_two import TestComponentScanFixtureTwo
from python_di.configs.component_scan import component_scan
from python_util.logger.logger import LoggerFacade


@component_scan(base_packages=['inject_tests.component_scan_fixture'],
                base_classes=[TestComponentScanFixtureTwo, torch.nn.Module])
class ComponentScanDecorated:
    pass


class ComponentScanTest(unittest.TestCase):
    def test_component_scan(self):
        c = ComponentScanDecorated
        assert c.component_scan
        assert len(c.sources) != 0
        assert len(c.sources) == 3
        assert os.path.join(os.path.dirname(__file__), 'fixtures') in c.sources
        assert os.path.join(os.path.dirname(__file__), 'fixtures', 'test_subdir') in c.sources
        LoggerFacade.info(f"Found sources {c.sources}")


if __name__ == '__main__':
    unittest.main()
