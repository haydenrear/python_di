import os.path
import typing
import unittest

import injector

from python_di.inject.context_builder.injection_context import InjectionContext
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.scopes.prototype_scope import prototype_scope_decorator, \
    prototype_scope_decorator_factory
from test_contexts.dependency_resolution_scan.dep_res_component_scan_referenced_package.circular_dep import \
    CircularDepFour
from test_contexts.test_component_scan.component_scan_class_reference_package.component_referenced import \
    ComponentReferenced
from test_contexts.test_component_scan.component_scan_referenced_package.component_referenced import \
    ComponentReferencedFromPackage
from test_contexts.test_component_scan.component_scan_referenced_package.configuration_referenced import \
    ConfigBeanFromPackageProduced
from test_contexts.test_component_scan.component_scan_referenced_package.other_component_with_deps import \
    OtherComponentReferencedFromPackage
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.component_referenced import \
    ProfileComponentReferencedFromPackage
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.config_prop import \
    TestEnableConfigProps, ConfigProp
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.configuration_referenced import \
    OtherProfileComponentFromConfiguration, OtherProfileComponentFromConfigurationNoDeps, \
    OtherComponentFromConfigurationNoDeps, OtherDifferentProfileComponentFromConfigurationNoDeps, HasLifecycle2
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.lifecycle_referenced import \
    HasLifecycle
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.multibindable_component_ref import \
    MultibindableInterface, MultibindableImpl, MultibindableImpl2
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.prototype_bean_ref import \
    TestPrototypeBean
from test_framework.assertions.assert_all import assert_all



class InjectorBuilder(unittest.TestCase):

    def test_inject_builder(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts', 'test_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))

        assert inject_ctx.ctx.contains_binding(ConfigBeanFromPackageProduced)
        assert inject_ctx.ctx.contains_binding(ComponentReferenced)
        assert inject_ctx.ctx.contains_binding(ComponentReferencedFromPackage)
        assert inject_ctx.ctx.contains_binding(OtherComponentReferencedFromPackage)

        other_component: OtherComponentReferencedFromPackage \
            = inject_ctx.ctx.get_interface(OtherComponentReferencedFromPackage)
        component_ref: ComponentReferencedFromPackage \
            = inject_ctx.ctx.get_interface(ComponentReferencedFromPackage)

        assert other_component.component_ref is not None
        assert other_component.component_ref == component_ref

    def test_profile_inject_builder(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'test_profiles_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))

        component_ref_test: ProfileComponentReferencedFromPackage \
            = inject_ctx.ctx.get_interface(ProfileComponentReferencedFromPackage, profile='test',
                                           scope=profile_scope)
        assert component_ref_test.name == 'test'
        component_ref_validation: ProfileComponentReferencedFromPackage \
            = inject_ctx.ctx.get_interface(ProfileComponentReferencedFromPackage, profile='validation',
                                           scope=profile_scope)
        assert component_ref_validation.name == 'validation'

    def test_prototype_config(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'test_profiles_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))
        prototype_created = inject_ctx.ctx.get_interface(TestPrototypeBean,
                                                         scope=prototype_scope_decorator(),
                                                         to_pass='hello')
        assert prototype_created.other_value is not None
        assert prototype_created.to_pass == 'hello'


    def test_inject_config(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'test_profiles_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))

        other_no_deps_component_validation_no_deps: OtherComponentFromConfigurationNoDeps \
            = inject_ctx.ctx.get_interface(OtherComponentFromConfigurationNoDeps, scope=injector.singleton)
        assert isinstance(other_no_deps_component_validation_no_deps, OtherComponentFromConfigurationNoDeps)
        assert other_no_deps_component_validation_no_deps.test_value == 'test'

        other_component_validation_no_deps: OtherProfileComponentFromConfigurationNoDeps \
            = inject_ctx.ctx.get_interface(OtherProfileComponentFromConfigurationNoDeps, profile='validation',
                                           scope=profile_scope)
        assert isinstance(other_component_validation_no_deps, OtherProfileComponentFromConfigurationNoDeps)
        assert other_component_validation_no_deps.test_value == 'test'
        other_component_validation_no_deps: OtherProfileComponentFromConfigurationNoDeps \
            = inject_ctx.ctx.get_interface(OtherProfileComponentFromConfigurationNoDeps, profile='test',
                                           scope=profile_scope)
        assert isinstance(other_component_validation_no_deps, OtherProfileComponentFromConfigurationNoDeps)
        assert other_component_validation_no_deps.test_value == 'test'

        other_component_validation_no_deps: OtherDifferentProfileComponentFromConfigurationNoDeps\
            = inject_ctx.ctx.get_interface(OtherDifferentProfileComponentFromConfigurationNoDeps, profile='test',
                                           scope=profile_scope)
        assert isinstance(other_component_validation_no_deps, OtherDifferentProfileComponentFromConfigurationNoDeps)
        assert other_component_validation_no_deps.test_value == 'test'


        other_component_validation_no_deps_: OtherDifferentProfileComponentFromConfigurationNoDeps \
            = inject_ctx.ctx.get_interface(OtherDifferentProfileComponentFromConfigurationNoDeps,
                                           profile='validation',
                                           scope=profile_scope)
        assert isinstance(other_component_validation_no_deps_, OtherDifferentProfileComponentFromConfigurationNoDeps)
        assert other_component_validation_no_deps_.test_value == 'validation'


        other_component_validation: OtherProfileComponentFromConfiguration \
            = inject_ctx.ctx.get_interface(OtherProfileComponentFromConfiguration, profile='validation',
                                           scope=profile_scope)
        assert other_component_validation.component_ref.name == 'validation'
        assert isinstance(other_component_validation, OtherProfileComponentFromConfiguration)
        other_component_test: OtherProfileComponentFromConfiguration \
            = inject_ctx.ctx.get_interface(OtherProfileComponentFromConfiguration, profile='test',
                                           scope=profile_scope)
        assert isinstance(other_component_test, OtherProfileComponentFromConfiguration)
        assert other_component_test.component_ref.name == 'test'


    def test_lifecycle(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'test_profiles_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))
        lifecycle_value: HasLifecycle = inject_ctx.ctx.get_interface(HasLifecycle)

        assert 'post_construct' in lifecycle_value.to_test.keys()
        assert 'test_autowire' in lifecycle_value.to_test.keys()
        assert 'validation_autowire' in lifecycle_value.to_test.keys()

        assert lifecycle_value.to_test['test_autowire'].component_ref.name == 'test'
        assert lifecycle_value.to_test['validation_autowire'].component_ref.name == 'validation'

        lifecycle_value: HasLifecycle2 = inject_ctx.ctx.get_interface(HasLifecycle2)

        assert 'post_construct' in lifecycle_value.to_test.keys()
        assert 'test_autowire' in lifecycle_value.to_test.keys()
        assert 'validation_autowire' in lifecycle_value.to_test.keys()

        assert lifecycle_value.to_test['test_autowire'].component_ref.name == 'test'
        assert lifecycle_value.to_test['validation_autowire'].component_ref.name == 'validation'

        config_prop: ConfigProp = inject_ctx.ctx.get_interface(ConfigProp)
        assert config_prop.value == 'hello'
        assert config_prop.test_value == 'hello there'


    def test_multibind(self):

        inject_ctx = InjectionContext()
        _ = inject_ctx.initialize_env()
        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'test_profiles_component_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))

        created = inject_ctx.ctx.get_interface(typing.List[MultibindableInterface])

        assert_all_values = assert_all()

        assert_all_values(len(created) == 2, f"Created had wrong number of values, was {created}")
        assert_all_values(all([isinstance(c, MultibindableInterface) for c in created]),
                          "Multbind interface was not correct values.")
        assert_all_values(not all([not isinstance(c, MultibindableImpl) for c in created]),
                          "Multbind did not have expected values")
        asserted = assert_all_values(not all([not isinstance(c, MultibindableImpl2) for c in created]),
                                     "Multibind did not have expected values")

        asserted()

    def test_circular_dep(self):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        assert env is not None

        to_scan = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_contexts',
                               'dependency_resolution_scan')
        inject_ctx.build_context({to_scan}, os.path.dirname(os.path.dirname(__file__)))
        c: CircularDepFour = inject_ctx.ctx.get_interface(CircularDepFour)
        assert c is not None

