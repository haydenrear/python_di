from python_di.configs.prototype import prototype_scope_bean, prototype_factory
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.configuration_referenced import \
    OtherProfileComponentFromConfiguration


@prototype_scope_bean()
class TestPrototypeBean:

    @prototype_factory()
    def __init__(self, other_value: OtherProfileComponentFromConfiguration,
                 to_pass: str):
        self.to_pass = to_pass
        self.other_value = other_value
