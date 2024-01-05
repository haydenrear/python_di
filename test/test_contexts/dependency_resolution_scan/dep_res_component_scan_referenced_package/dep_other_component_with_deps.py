import injector

from python_di.configs.bean import bean
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from test_contexts.dependency_resolution_scan.dep_res_component_scan_referenced_package.dep_component_referenced import \
    DepProfileComponentReferencedFromPackage
from test_contexts.test_component_scan.component_scan_referenced_package.component_referenced import \
    ComponentReferencedFromPackage


@component()
class DepOtherProfileComponentReferencedFromPackage:
    def __init__(self, component_ref: DepProfileComponentReferencedFromPackage):
        self.component_ref = component_ref

    @classmethod
    @bean(self_factory=True, profile='test', scope=profile_scope)
    def build_test_config(cls, component_referenced: DepProfileComponentReferencedFromPackage):
        return DepOtherProfileComponentReferencedFromPackage(component_referenced)

    @classmethod
    @bean(self_factory=True, profile='validation', scope=profile_scope)
    def build_validation_config(cls, component_referenced: DepProfileComponentReferencedFromPackage):
        return DepOtherProfileComponentReferencedFromPackage(component_referenced)

