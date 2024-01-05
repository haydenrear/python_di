import injector

from python_di.configs.component import component
from test_contexts.dependency_resolution_scan.dep_res_component_scan_referenced_package.dep_component_referenced import \
    DepProfileComponentReferencedFromPackage


@component()
class CircularDepOne:
    @injector.inject
    def __init__(self, component_ref: DepProfileComponentReferencedFromPackage):
        self.component_ref = component_ref


@component()
class CircularDepTwo:
    @injector.inject
    def __init__(self, component_ref: CircularDepOne):
        self.component_ref = component_ref


@component()
class CircularDepThree:
    @injector.inject
    def __init__(self, component_ref: CircularDepTwo):
        self.component_ref = component_ref


@component()
class CircularDepFour:
    @injector.inject
    def __init__(self, component_ref: CircularDepOne):
        self.component_ref = component_ref
