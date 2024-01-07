import typing

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.inject.context_factory.context_factory import ConfigurationPropertiesFactory


def enable_configuration_properties(config_props: typing.List[typing.Type[ConfigurationProperties]]):
    def class_decorator_inner(cls):
        cls.config_properties_context_factory = True
        cls.config_props_context_factory = lambda: _get_factories(cls)
        return cls

    def _get_factories(cls):
        props = _get_ctx_properties_factory(cls)
        props.extend(_get_properties_lifecycle())
        return props

    def _get_ctx_properties_factory(cls):
        return [ConfigurationPropertiesFactory([
            ConfigurationPropertiesFactory.create_inject_ty_metadata(c)
            for c in config_props
        ], cls)]

    def _get_properties_lifecycle():
        return [c for i in filter(lambda config_prop: hasattr(config_prop, 'context_factory_provider'), config_props)
                for c in i.context_factory_provider.context_factory]

    return class_decorator_inner
