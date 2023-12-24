import abc
import typing

from python_di.configs.base_config import DiConfiguration
from python_di.inject.context_factory.context_factory import ConfigurationPropertiesFactory, \
    ConfigurationFactory, PrototypeComponentFactory, PostConstructFactory, AutowireFactory, PreConstructFactory
from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import ComponentFactory

T = typing.TypeVar("T")


class ContextFactoryProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def context_factory(self) -> list[ContextFactory]:
        pass


class ConfigurationPropertiesFactoriesProvider(ContextFactoryProvider, abc.ABC):

    @property
    @abc.abstractmethod
    def context_factory(self) -> list[ConfigurationPropertiesFactory]:
        pass


DiConfigurationT = typing.TypeVar("DiConfigurationT", covariant=True, bound=DiConfiguration)


class ConfigurationFactoryProvider(ContextFactoryProvider, abc.ABC):

    @property
    @abc.abstractmethod
    def context_factory(self) -> list[ConfigurationFactory]:
        pass


class ComponentFactoryProvider(ContextFactoryProvider, abc.ABC):

    @property
    @abc.abstractmethod
    def context_factory(self) -> list[ComponentFactory]:
        pass


class PrototypeFactoryProvider(ContextFactoryProvider, abc.ABC):

    @property
    @abc.abstractmethod
    def context_factory(self) -> list[PrototypeComponentFactory]:
        pass


class InjectableContextFactoryProvider(ContextFactoryProvider, abc.ABC):
    @property
    @abc.abstractmethod
    def context_factory(self) -> list[typing.Union[PostConstructFactory, AutowireFactory, PreConstructFactory]]:
        pass
