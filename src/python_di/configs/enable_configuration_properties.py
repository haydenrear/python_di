import typing

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.inject.context_factory.context_factory import ConfigurationPropertiesFactory


def enable_configuration_properties(config_props: typing.List[typing.Type[ConfigurationProperties]]):
    def class_decorator_inner(cls):
        cls.config_properties_context_factory = True
        cls.context_factory = lambda: _get_ctx_properties_factory(cls)
        return cls

    def _get_ctx_properties_factory(cls):
        return [ConfigurationPropertiesFactory([
            ConfigurationPropertiesFactory.create_inject_ty_metadata(c)
            for c in config_props
        ], cls)]

    return class_decorator_inner
