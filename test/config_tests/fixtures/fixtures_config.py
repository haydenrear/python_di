from config_tests.fixtures.to_inject_component import ToInjectComponent
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration


@configuration()
@component_scan(base_classes=[ToInjectComponent])
class ToInjectComponentConfig:
    pass

