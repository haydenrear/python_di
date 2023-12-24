from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.reflect_scanner.scanner_properties import ScannerProperties


@enable_configuration_properties(config_props=[ScannerProperties])
class TestComponentScanFixtureTwo:
    pass
