import injector

from python_di.configs.bean import bean
from python_di.configs.di_configuration import configuration
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from test_contexts.dependency_resolution_scan.dep_res_component_scan_referenced_package.dep_component_referenced import \
    DepProfileComponentReferencedFromPackage


class DepOtherProfileComponentFromConfiguration:
    def __init__(self, component_ref: DepProfileComponentReferencedFromPackage):
        self.component_ref = component_ref


class DepOtherProfileComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


class DepOtherDifferentProfileComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


class DepOtherComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


@configuration()
class DepProfileConfigurationFromPackageReferenced:

    @bean(profile=['test', 'validation'], scope=profile_scope)
    def other_component_configuration(
            self,
            component_referenced: DepProfileComponentReferencedFromPackage
    ) -> DepOtherProfileComponentFromConfiguration:
        return DepOtherProfileComponentFromConfiguration(component_referenced)

    @bean(profile=['test', 'validation'], scope=profile_scope)
    def other_component_configuration_no_deps(self, ) -> DepOtherProfileComponentFromConfigurationNoDeps:
        return DepOtherProfileComponentFromConfigurationNoDeps('test')

    @bean(profile='validation', scope=profile_scope)
    def other_diff_validation_component_configuration_no_deps(self) \
            -> DepOtherDifferentProfileComponentFromConfigurationNoDeps:
        other_diff = DepOtherDifferentProfileComponentFromConfigurationNoDeps('validation')
        return other_diff

    @bean(profile='test', scope=profile_scope)
    def other_diff_test_component_configuration_no_deps(self) -> DepOtherDifferentProfileComponentFromConfigurationNoDeps:
        other_diff = DepOtherDifferentProfileComponentFromConfigurationNoDeps('test')
        return other_diff

    @bean()
    def other_component_no_deps(self) -> DepOtherComponentFromConfigurationNoDeps:
        return DepOtherComponentFromConfigurationNoDeps('test')
