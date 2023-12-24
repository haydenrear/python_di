import os
import unittest

import python_util.io_utils.file_dirs
from python_di.env.env_factories import Factories, Factory
from python_di.env.properties_loader import PropertyLoader


class TestPropertyLoader(unittest.TestCase):
    def test_property_loader(self):
        resources_value = python_util.io_utils.file_dirs.get_resources_dir(__file__)
        assert resources_value is not None
        prop_loader = PropertyLoader(os.path.join(resources_value, 'application.yml'))
        factories = prop_loader.load_property_by_ty(Factories, 'env_factories')
        assert isinstance(factories, Factories)
        assert isinstance(factories.factories['main_profile'], list)
        assert isinstance(factories.factories['main_profile'][0], Factory)
