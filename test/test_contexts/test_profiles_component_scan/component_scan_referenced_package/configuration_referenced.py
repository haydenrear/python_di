import injector

from python_di.configs.autowire import injectable, post_construct, autowire
from python_di.configs.bean import bean
from python_di.configs.di_configuration import configuration
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.component_referenced import \
    ProfileComponentReferencedFromPackage


class OtherProfileComponentFromConfiguration:
    def __init__(self, component_ref: ProfileComponentReferencedFromPackage):
        self.component_ref = component_ref


class OtherProfileComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


class OtherDifferentProfileComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


class OtherComponentFromConfigurationNoDeps:
    def __init__(self, test_value: str = None):
        self.test_value = test_value


@injectable()
class HasLifecycle2:

    def __init__(self):
        self.to_test = {}

    @post_construct
    def has_post_construct(self):
        self.to_test['post_construct'] = True

    @autowire(injectable_profile='test')
    def set_value(self, to_set: OtherProfileComponentFromConfiguration):
        self.to_test['test_autowire'] = to_set
        print('hello')

    @autowire(injectable_profile='validation')
    def set_validation_value(self, to_set: OtherProfileComponentFromConfiguration):
        self.to_test['validation_autowire'] = to_set


@configuration()
class ProfileConfigurationFromPackageReferenced:

    @bean(profile=['test', 'validation'], scope=profile_scope)
    def other_component_configuration(
            self,
            component_referenced: ProfileComponentReferencedFromPackage
    ) -> OtherProfileComponentFromConfiguration:
        return OtherProfileComponentFromConfiguration(component_referenced)

    @bean(profile=['test', 'validation'], scope=profile_scope)
    def has_lifecycle(self) -> HasLifecycle2:
        return HasLifecycle2()

    @bean(profile=['test', 'validation'], scope=profile_scope)
    def other_component_configuration_no_deps(self, ) -> OtherProfileComponentFromConfigurationNoDeps:
        return OtherProfileComponentFromConfigurationNoDeps('test')

    @bean(profile='validation', scope=profile_scope)
    def other_diff_validation_component_configuration_no_deps(self) \
            -> OtherDifferentProfileComponentFromConfigurationNoDeps:
        other_diff = OtherDifferentProfileComponentFromConfigurationNoDeps('validation')
        return other_diff

    @bean(profile='test', scope=profile_scope)
    def other_diff_test_component_configuration_no_deps(self) -> OtherDifferentProfileComponentFromConfigurationNoDeps:
        other_diff = OtherDifferentProfileComponentFromConfigurationNoDeps('test')
        return other_diff

    @bean()
    def other_component_no_deps(self) -> OtherComponentFromConfigurationNoDeps:
        return OtherComponentFromConfigurationNoDeps('test')
