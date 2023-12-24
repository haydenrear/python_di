from python_di.configs.component_scan import component_scan
from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.reflect_scanner.scanner_properties import ScannerProperties
from test_contexts.test_component_scan.component_scan_class_reference_package.component_scan_referenced import \
    ToReferenceClass


@component_scan(
    base_classes=[ToReferenceClass],
    base_packages=["test_contexts.test_component_scan.component_scan_referenced_package.component_referenced"]
)
class ContainsComponentScan:
    pass
