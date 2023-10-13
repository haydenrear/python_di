import unittest

from python_di.properties.configuration_properties_decorator import configuration_properties


@configuration_properties(prefix_name='prefix')
class TestBaseProps:
    def __init__(self, one: str = 'test_value'):
        self.one = one


class BasePropsTest(unittest.TestCase):
    def test_inject_properties(self):
        base = TestBaseProps()
        assert base.one == 'test_value'
