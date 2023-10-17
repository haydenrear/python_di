import unittest

from python_di.configs.component import component


@component()
class Test:
    pass


class ComponentInjectorTest(unittest.TestCase):
    def test_component(self):
        pass


if __name__ == '__main__':
    unittest.main()
