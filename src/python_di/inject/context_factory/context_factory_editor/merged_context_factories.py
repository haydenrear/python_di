import typing

from python_di.inject.context_factory.context_factory import ConfigurationPropertiesFactory, \
    ConfigurationFactory, ComponentContextFactory, PrototypeComponentFactory, LifecycleFactory
from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.context_factory_editor.base_merge_context_factory import MergedContextFactory, \
    MergedContextFactoriesEditor


class MergedConfigurationContextFactory(MergedContextFactory):
    pass


class MergedConfigurationContextFactoriesEditor(MergedContextFactoriesEditor):

    @property
    def merged_context_factory(self) -> typing.Type:
        return MergedConfigurationContextFactory

    def is_factory_ty(self, f: ContextFactory):
        return isinstance(f, ConfigurationFactory)

    def ordering(self) -> int:
        return -10


class MergedComponentContextFactory(MergedContextFactory):
    pass


class MergedComponentContextFactoriesEditor(MergedContextFactoriesEditor):
    @property
    def merged_context_factory(self) -> typing.Type:
        return MergedComponentContextFactory

    def is_factory_ty(self, f: ContextFactory):
        return isinstance(f, ComponentContextFactory)

    def ordering(self) -> int:
        return -10


class MergedInjectionContextFactory(MergedContextFactory):
    pass


class MergedInjectionContextFactoriesEditor(MergedContextFactoriesEditor):

    @property
    def merged_context_factory(self) -> typing.Type:
        return MergedInjectionContextFactory

    def is_factory_ty(self, f: ContextFactory):
        return isinstance(f, LifecycleFactory)

    def ordering(self) -> int:
        return -10


class PrototypeContextFactory(MergedContextFactory):
    pass


class PrototypeContextFactoriesEditor(MergedContextFactoriesEditor):
    """
    # TODO: add to this any arbitrary update to properties using @test_property.
    """

    @property
    def merged_context_factory(self) -> typing.Type:
        return PrototypeContextFactory

    def is_factory_ty(self, f: ContextFactory):
        return isinstance(f, PrototypeComponentFactory)

    def ordering(self) -> int:
        """
        Configuration properties can go first.
        :return:
        """
        return -10


class ConfigurationPropertiesContextFactory(MergedContextFactory):
    pass


class ConfigurationPropertiesContextFactoriesEditor(MergedContextFactoriesEditor):
    """
    # TODO: add to this any arbitrary update to properties using @test_property.
    """

    @property
    def merged_context_factory(self) -> typing.Type:
        return ConfigurationPropertiesContextFactory

    def is_factory_ty(self, f: ContextFactory):
        return isinstance(f, ConfigurationPropertiesFactory)

    def ordering(self) -> int:
        """
        Configuration properties can go first.
        :return:
        """
        return -8
