import os
import unittest

import pydantic

import python_util.io_utils.file_dirs
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.env_factories import Factories, Factory
from python_di.env.properties_loader import PropertyLoader
from python_di.env.property_source import PropertySource

from python_di.env import main_profile

class WhateverValue(ConfigurationProperties):
    whatever: str

class TestPropertyLoader(unittest.TestCase):
    def test_property_loader(self):
        os.environ['X_WHATEVER'] = 'do_this'
        resources_value = python_util.io_utils.file_dirs.get_resources_dir(__file__)
        assert resources_value is not None
        prop_loader = PropertyLoader(os.path.join(resources_value, 'application.yml'))
        factories = prop_loader.load_property_by_ty(Factories, 'env_factories')
        assert isinstance(factories, Factories)
        assert isinstance(factories.factories, list)
        assert isinstance(factories.factories[0], Factory)

        prop_loader = PropertyLoader(os.path.join(resources_value, 'application.yml'))
        what = prop_loader.load_property_by_ty(WhateverValue, 'okay')
        p = PropertySource(main_profile.get_default_profile(), secrets_overrides={'X_WHATEVER': 'okay'})
        p.add_config_property('okay', what)
        found: WhateverValue = p.get_prop('okay')
        assert found.whatever == 'okay'




