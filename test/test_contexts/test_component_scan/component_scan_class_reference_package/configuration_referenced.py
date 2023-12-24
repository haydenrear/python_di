from python_di.configs.bean import bean
from python_di.configs.di_configuration import configuration


class ConfigBeanProduced:
    pass


@configuration()
class ConfigurationReferenced:

    @bean()
    def config_bean(self) -> ConfigBeanProduced:
        return ConfigBeanProduced()
