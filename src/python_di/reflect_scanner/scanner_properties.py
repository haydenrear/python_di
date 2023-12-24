import os

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties


@configuration_properties(
    prefix_name='scanner',
    fallback=os.path.join(os.path.dirname(__file__),
                          'reflect-scanner-fallback-application.yml')
)
class ScannerProperties(ConfigurationProperties):
    src_file: str
    num_up: int
