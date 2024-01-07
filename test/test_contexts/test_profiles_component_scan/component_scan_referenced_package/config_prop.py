import os
from typing import Optional

from python_di.configs.autowire import post_construct, injectable
from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties


@injectable()
@configuration_properties(prefix_name='test_prefix',
                          fallback=os.path.join(os.path.dirname(__file__),
                                                'test-application.yml'))
class ConfigProp(ConfigurationProperties):
    test_value: str

    value: Optional[str]

    @post_construct
    def post_value(self):
        self.value = "hello"


@enable_configuration_properties(config_props=[ConfigProp])
class TestEnableConfigProps:
    pass
