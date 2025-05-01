from config_tests.fixtures.to_inject_component import ToInjectComponent
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties

@configuration()
@component_scan(base_classes=[ToInjectComponent])
class ToInjectComponentConfig:
    pass

