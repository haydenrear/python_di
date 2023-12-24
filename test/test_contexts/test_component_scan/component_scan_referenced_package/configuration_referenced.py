from python_di.configs.bean import bean
from python_di.configs.di_configuration import configuration


class ConfigBeanFromPackageProduced:
    pass


@configuration()
class ConfigurationFromPackageReferenced:

    @bean()
    def config_bean(self) -> ConfigBeanFromPackageProduced:
        return ConfigBeanFromPackageProduced()
