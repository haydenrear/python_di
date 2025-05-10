import os

from config_tests.fixtures.component import TestComponent
from config_tests.fixtures.fixtures_config import ToInjectComponentConfig
from python_di.configs.test import test_booter, tst_config


@test_booter(scan_root_module=ToInjectComponentConfig, profile_name_override='python_di_test')
class TestBoot:
    pass


