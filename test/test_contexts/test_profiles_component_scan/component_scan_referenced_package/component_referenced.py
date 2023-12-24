import injector

from python_di.configs.bean import bean
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope


@component()
class ProfileComponentReferencedFromPackage:
    def __init__(self, name: str = ''):
        self.name = name

    @classmethod
    @bean(self_factory=True, profile='test', scope=profile_scope)
    def build_test_config(cls):
        return ProfileComponentReferencedFromPackage("test")

    @classmethod
    @bean(self_factory=True, profile='validation', scope=profile_scope)
    def build_validation_config(cls):
        return ProfileComponentReferencedFromPackage("validation")
