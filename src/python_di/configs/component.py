import dataclasses
import typing
from typing import Optional

import injector

from python_di.configs.di_util import get_underlying, DiUtilConstants, get_wrapped_fn, retrieve_factory
from python_di.inject.composite_injector import profile_scope
from python_di.inject.inject_context_di import inject_context_di
from python_di.inject.injector_provider import InjectionContext
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class ComponentSelfFactory:
    profile: str
    priority: int
    ctx: dict
    factory: typing.Callable
    cls: typing.Type
    scope: injector.ScopeDecorator


@dataclasses.dataclass(init=True)
class ComponentFactory:
    scope: injector.ScopeDecorator
    cls: typing.Type
    underlying: typing.Type
    binding: list[typing.Type]
    profiles: typing.Union[str, list[str], None]
    component_self_factory: dict[str, ComponentSelfFactory]


@inject_context_di()
def register_component_factory(component_factory_data: ComponentFactory, ctx: Optional[InjectionContext] = None):

    component_factory_data: ComponentFactory
    profile = component_factory_data.profiles
    scope = component_factory_data.scope
    binding = component_factory_data.binding
    cls = component_factory_data.cls

    if isinstance(profile, list):
        assert scope == profile_scope
        for p in profile:
            ctx.register_component(cls, bindings=binding, scope=scope, profile=p)
    elif isinstance(profile, str):
        ctx.register_component(cls, binding, scope, profile)
        from python_di.env.env_properties import DEFAULT_PROFILE
        if profile != DEFAULT_PROFILE:
            assert scope is not None and scope != injector.singleton
            assert scope == profile_scope
            ctx.register_component(cls, binding, scope, DEFAULT_PROFILE)
    elif scope is None or scope == injector.singleton:
        ctx.register_component(cls, bindings=binding, scope=injector.singleton)
    elif (scope is not None and len(component_factory_data.component_self_factory) == 0
          and not ctx.contains_interface(cls)):
        ctx.register_component(cls, bindings=binding, scope=scope)

    for c, f in component_factory_data.component_self_factory.items():
        cls = f.cls
        self_bean_factory = f.factory
        to_construct = f.ctx
        ctx.register_component_value([cls], self_bean_factory(cls, **to_construct),
                                     f.scope, f.priority, f.profile)


def component(bind_to: list[type] = None,
              profile: typing.Union[str, None, list[str]] = None,
              scope: Optional[injector.ScopeDecorator] = None):

    def class_decorator_inner(cls):
        self_factories = create_self_factories(cls)
        binding = get_bindings(cls)
        factory = ComponentFactory(
            scope=scope, cls=cls, underlying=cls,
            binding=binding, profiles=profile,
            component_self_factory=self_factories
        )
        register_component_factory(factory)
        return cls

    def get_bindings(cls):
        binding = bind_to if bind_to is not None else [cls]
        if cls not in binding:
            binding.append(cls)
        return binding

    def create_self_factories(cls):
        component_self_factories: dict[str, ComponentSelfFactory] = {}
        for class_property_name, class_property_method_value in cls.__dict__.items():
            if hasattr(cls, class_property_name):
                potential_self_bean_factory = getattr(cls, class_property_name)
                if (hasattr(potential_self_bean_factory, DiUtilConstants.wrapped_fn.name)
                        and potential_self_bean_factory.wrapped_fn.self_factory):
                    self_bean_factory, wrapped = get_wrapped_fn(potential_self_bean_factory)
                    config_profile = self_bean_factory.profile
                    config_profile = retrieve_profiles(config_profile)
                    assert isinstance(config_profile, list)
                    for p in config_profile:
                        do_inject, to_construct = retrieve_factory(self_bean_factory, p)
                        if not do_inject:
                            LoggerFacade.error(f"Error injecting self bean factory for {cls}.")
                        else:
                            priority = self_bean_factory.priority
                            self_factory_scope = get_create_self_factory_scope(self_bean_factory)
                            LoggerFacade.info(f"Found bean self factory for {config_profile} and {cls}.")
                            component_self_factories[p] = ComponentSelfFactory(
                                p, priority, to_construct, self_bean_factory,
                                cls, self_factory_scope)

        return component_self_factories

    def retrieve_profiles(config_profile):
        if config_profile is None:
            config_profile = [profile]
        elif isinstance(config_profile, str):
            config_profile = [config_profile]
        return config_profile

    def get_create_self_factory_scope(self_bean_factory):
        self_factory_scope = self_bean_factory.scope if self_bean_factory.scope is not None else None
        if self_factory_scope is None and scope is not None:
            self_factory_scope = scope
        if self_factory_scope is None:
            self_factory_scope = injector.singleton
        return self_factory_scope

    return class_decorator_inner
