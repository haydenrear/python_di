import abc
import dataclasses
import typing
from typing import Optional

import injector

from python_di.configs.base_config import DiConfiguration
from python_di.configs.constants import DiUtilConstants
from python_di.env.base_env_properties import Environment
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.profile_config_props import ProfileProperties
from python_di.inject.context_factory.base_context_factory import CallableFactory, ContextFactory
from python_di.inject.context_factory.context_factory_executor.metadata_factory import LifeCycleMetadataFactory

from python_di.inject.context_factory.type_metadata.inject_ty_metadata import ConfigurationPropertiesInjectTypeMetadata, ComponentFactoryInjectTypeMetadata, ComponentFactory, \
    ComponentSelfFactory, PrototypeFactory, LifecycleInjectTypeMetadata
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata, HasFnArgs
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn

T = typing.TypeVar("T")


@dataclasses.dataclass(init=True)
class ConfigurationPropertiesFactory(ContextFactory):
    config_props: typing.List[ConfigurationPropertiesInjectTypeMetadata]
    enable_configs: typing.Type

    @property
    def inject_types(self) -> list[ConfigurationPropertiesInjectTypeMetadata]:
        return [self.create_inject_ty_metadata(m.ty_to_inject) for m in self.config_props]

    @classmethod
    @autowire_fn()
    def create_inject_ty_metadata(cls, c: typing.Type[ConfigurationProperties], profile_properties: ProfileProperties):
        return ConfigurationPropertiesInjectTypeMetadata(
            c,
            getattr(c, DiUtilConstants.proxied.name) if hasattr(c, DiUtilConstants.proxied.name)
            else c,
            profile_properties.default_profile.profile_name,
            profile_properties.default_profile.priority,
            injector.singleton, {}, [],
            getattr(c, DiUtilConstants.prefix_name.name) if hasattr(c, DiUtilConstants.prefix_name.name)
            else None
        )


class ConfigurationFactory(DiConfiguration, ContextFactory, abc.ABC):

    def __init__(self,
                 profile: Optional[str],
                 priority: Optional[int],
                 cls: typing.Type,
                 underlying: typing.Type):
        self.underlying = underlying
        self.cls = cls
        self.priority = priority
        self.profile = profile


@dataclasses.dataclass(init=True)
class ComponentContextFactory(ContextFactory):
    _inject_types: list[ComponentFactoryInjectTypeMetadata]

    @property
    def inject_types(self) -> list[InjectTypeMetadata]:
        return self._inject_types

    def retrieve_component_factory(self):
        out = None
        for c in self.inject_types:
            if isinstance(c, ComponentFactory):
                if out is not None:
                    raise ValueError("Only one component factory allowed.")
                out = c._to_call

        return out

    def retrieve_self_factories(self):
        out = {}
        for c in self.inject_types:
            if isinstance(c, ComponentSelfFactory):
                if c.profile is None:
                    out[Environment.default_profile().profile_name] = c
                elif isinstance(c.profile, str):
                    out[c.profile] = c
                elif isinstance(c.profile, list):
                    for p in c.profile:
                        if p in out.keys():
                            raise ValueError(f"Multiple profiles defined for {c}")
                        out[p] = c

        return out


class PrototypeComponentFactory(ContextFactory, InjectTypeMetadata):

    def __init__(self, ty_to_inject: typing.Type[T], underlying: typing.Type, profile: typing.Union[str, list[str]],
                 priority: int, scope: injector.ScopeDecorator, dependencies: dict[str, ...],
                 bindings: list[typing.Type], wrapped_fn: typing.Callable, factory: typing.Type[PrototypeFactory]):
        super().__init__(ty_to_inject, underlying, profile, priority, scope, dependencies, bindings)
        self.wrapped_fn = wrapped_fn
        self.factory = factory

    @property
    def inject_types(self) -> list[InjectTypeMetadata]:
        return [self]

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                PrototypeComponentFactory(self.ty_to_inject, self.underlying, p, self.priority,
                                          self.scope, self.dependencies, self.bindings,
                                          self.wrapped_fn, self.factory)
                for p in self.profile
            ]


class LifecycleFactory(CallableFactory, ContextFactory, HasFnArgs, abc.ABC):

    def __init__(self,
                 cls_self_method: typing.Type[T],
                 underlying: typing.Type,
                 _to_call: typing.Callable,
                 dependency_tys: dict[str, typing.Type],
                 lifecycle_metadata: LifeCycleMetadataFactory):
        self.args = None
        self._to_call = _to_call
        self.lifecycle_metadata = lifecycle_metadata
        self.dependency_tys = dependency_tys
        self._fn_args = self.dependency_tys
        self.underlying = underlying
        self.cls_self_method = cls_self_method

    @property
    def fn_args(self) -> dict[str, type]:
        return self._fn_args

    def to_call(self) -> typing.Callable:
        return self._to_call

    @property
    def inject_types(self) -> list[InjectTypeMetadata]:
        return [
            LifecycleInjectTypeMetadata(self.cls_self_method,
                                        self.underlying,
                                        self.lifecycle_metadata.injectable_profile,
                                        self.lifecycle_metadata.injectable_priority,
                                        self.lifecycle_metadata.scope_decorator,
                                        self.dependency_tys, [],
                                        self.lifecycle_metadata.life_cycle_hook,
                                        self.lifecycle_metadata.life_cycle_type,
                                        self._to_call,
                                        self.args)
        ]


class PostConstructFactory(LifecycleFactory):
    pass


class AutowireFactory(LifecycleFactory):
    pass


class PreConstructFactory(LifecycleFactory):
    pass
