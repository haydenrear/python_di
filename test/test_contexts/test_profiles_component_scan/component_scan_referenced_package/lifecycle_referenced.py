import injector

from python_di.configs.autowire import post_construct, autowire, injectable
from python_di.configs.component import component
from test_contexts.test_profiles_component_scan.component_scan_referenced_package.configuration_referenced import \
    OtherProfileComponentFromConfiguration


@component()
@injectable()
class HasLifecycle:

    @injector.inject
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


