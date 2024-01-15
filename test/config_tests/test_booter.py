import os

from python_di.configs.test import test_booter


@test_booter(scan_root_directory=os.path.dirname(os.path.dirname(__file__)))
class TestBoot:
    pass


