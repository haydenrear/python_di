import abc

from python_di.configs.constants import ContextFactoryIdentifiers
from python_di.inject.context_factory.base_context_factory import ContextFactory


class ContextFactoryExtract(abc.ABC):

    @abc.abstractmethod
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        pass

    @abc.abstractmethod
    def matches(self, value: ...) -> bool:
        pass


class ConfigurationContextFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.context_factory

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.configuration_context_factory.name)


class ComponentContextFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.context_factory

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.component_context_factory.name)


class ContextFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.context_factory

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.component_context_factory.name)


class InjectableFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.context_factory_provider.context_factory

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.injectable_context_factory.name)


class ConfigurationPropertiesFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.config_props_context_factory()

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.config_properties_context_factory.name)


class PrototypeFactoryExtract(ContextFactoryExtract):
    def extract_context_factory(self, value: ...) -> list[ContextFactory]:
        return value.context_factory

    def matches(self, value: ...) -> bool:
        return hasattr(value, ContextFactoryIdentifiers.prototype_bean_factory_ty.name)
