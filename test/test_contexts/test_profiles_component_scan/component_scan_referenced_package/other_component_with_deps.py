import injector

from python_di.configs.bean import bean
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from test_contexts.test_component_scan.component_scan_referenced_package.component_referenced import \
    ComponentReferencedFromPackage
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.component_referenced import \
    ProfileComponentReferencedFromPackage


@component()
class OtherProfileComponentReferencedFromPackage:
    def __init__(self, component_ref: ProfileComponentReferencedFromPackage):
        self.component_ref = component_ref

    @classmethod
    @bean(self_factory=True, profile='test', scope=profile_scope)
    def build_test_config(cls, component_referenced: ProfileComponentReferencedFromPackage):
        return OtherProfileComponentReferencedFromPackage(component_referenced)

    @classmethod
    @bean(self_factory=True, profile='validation', scope=profile_scope)
    def build_validation_config(cls, component_referenced: ProfileComponentReferencedFromPackage):
        return OtherProfileComponentReferencedFromPackage(component_referenced)

