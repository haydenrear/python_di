import injector

from config_tests.fixtures.component import TestComponent
from python_di.configs.component import component


@component()
class ToInjectComponent:
    @injector.inject
    def __init__(self, c: TestComponent):
        self.c = c
