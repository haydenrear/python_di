import unittest

from python_di.env.env_factories import Factories, Factory
from python_di.env.properties_loader import PropertyLoader


class TestPropertyLoader(unittest.TestCase):
    def test_property_loader(self):
        prop_loader = PropertyLoader('resources/application.yml')
        factories = prop_loader.load_property_by_ty(Factories, 'env_factories')
        assert isinstance(factories, Factories)
        assert isinstance(factories.factories['test'], list)
        assert isinstance(factories.factories['test'][0], Factory)
