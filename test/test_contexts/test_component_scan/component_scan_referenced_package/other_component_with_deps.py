import injector

from python_di.configs.component import component
from test_contexts.test_component_scan.component_scan_referenced_package.component_referenced import \
    ComponentReferencedFromPackage


@component()
class OtherComponentReferencedFromPackage:
    @injector.inject
    def __init__(self, component_ref: ComponentReferencedFromPackage):
        self.component_ref = component_ref
