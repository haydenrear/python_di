import abc

from python_di.configs.constants import LifeCycleHook
from python_di.inject.context_factory.context_factory import PrototypeComponentFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import ConfigurationPropertiesInjectTypeMetadata, ComponentFactoryInjectTypeMetadata, ComponentSelfFactory, \
    ComponentFactory, BeanComponentFactory, LifecycleInjectTypeMetadata
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata
from python_di.inject.context_factory.context_factory_executor.register_factory import register_bean_component_factory, \
    register_prototype_component_factory, \
    do_lifecycle_hook, register_component_self_factory, register_configuration_properties, register_component_factory


class InjectionContextArgs(abc.ABC):
    pass


class InjectMetadataExecutor(abc.ABC):

    @abc.abstractmethod
    def execute(self,
                context_factory: InjectTypeMetadata,
                injection_context_args: InjectionContextArgs):
        pass

    @abc.abstractmethod
    def matches(self, context_factory: InjectTypeMetadata,
                injection_context_args: InjectionContextArgs) -> bool:
        pass


class RegisterFactoryMetadataExecutor(InjectMetadataExecutor):
    def execute(self,
                context_factory: InjectTypeMetadata,
                injection_context_args: InjectionContextArgs):
        register_factory(context_factory, injection_context_args)

    def matches(self, context_factory: InjectTypeMetadata, injection_context_args: InjectionContextArgs) -> bool:
        return (isinstance(context_factory, ComponentFactoryInjectTypeMetadata)
                or isinstance(context_factory, BeanComponentFactory)
                or isinstance(context_factory, ConfigurationPropertiesInjectTypeMetadata)
                or isinstance(context_factory, PrototypeComponentFactory)
                or isinstance(context_factory, LifecycleInjectTypeMetadata))


class LifecycleHookMetadataExecutor(InjectMetadataExecutor):
    def __init__(self, hook: LifeCycleHook):
        self.hook = hook

    def execute(self,
                context_factory: LifecycleInjectTypeMetadata,
                injection_context_args: InjectionContextArgs):
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        assert isinstance(injection_context_args, InjectionContextInjectorContextArgs)
        do_lifecycle_hook(context_factory, injection_context_args.injection_context_injector)

    def matches(self, context_factory: InjectTypeMetadata, injection_context_args: InjectionContextArgs) -> bool:
        return (isinstance(context_factory, LifecycleInjectTypeMetadata)
                and context_factory.lifecycle == self.hook)


class AutowireMetadataExecutor(LifecycleHookMetadataExecutor):
    def __init__(self):
        super().__init__(LifeCycleHook.autowire)


class PreConstructMetadataExecutor(LifecycleHookMetadataExecutor):
    def __init__(self):
        super().__init__(LifeCycleHook.pre_construct)


class PostConstructMetadataExecutor(LifecycleHookMetadataExecutor):
    def __init__(self):
        super().__init__(LifeCycleHook.post_construct)


def register_factory(inject_type_metadata: InjectTypeMetadata, factory_metadata: InjectionContextArgs):
    from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
    assert isinstance(factory_metadata, InjectionContextInjectorContextArgs)
    if isinstance(inject_type_metadata, BeanComponentFactory):
        register_bean_component_factory(inject_type_metadata, factory_metadata.injection_context_injector)
    elif isinstance(inject_type_metadata, ComponentFactory):
        register_component_factory(inject_type_metadata, factory_metadata.injection_context_injector)
    elif isinstance(inject_type_metadata, ComponentSelfFactory):
        register_component_self_factory(inject_type_metadata, factory_metadata.injection_context_injector)
    elif isinstance(inject_type_metadata, ConfigurationPropertiesInjectTypeMetadata):
        register_configuration_properties(inject_type_metadata, factory_metadata.injection_context_injector)
    elif isinstance(inject_type_metadata, PrototypeComponentFactory):
        register_prototype_component_factory(inject_type_metadata, factory_metadata.injection_context_injector)
