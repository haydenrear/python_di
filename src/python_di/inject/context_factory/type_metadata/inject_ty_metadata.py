import abc
import typing
from typing import Optional

import injector

from python_di.configs.constants import LifeCycleHook, FnTy
from python_di.inject.context_factory.base_context_factory import CallableFactory
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata

T = typing.TypeVar("T")


class ConfigurationPropertiesInjectTypeMetadata(InjectTypeMetadata):
    prefix: str
    location: Optional[str] = None
    override_properties: dict[str, ...] = None

    def __init__(self, ty_to_inject: typing.Type[T], underlying: typing.Type, profile: typing.Union[str, list[str]],
                 priority: int, scope: injector.ScopeDecorator, dependencies: dict[str, ...],
                 bindings: list[typing.Type], prefix: str, location: Optional[str] = None,
                 override_properties: dict[str, str] = None):
        super().__init__(ty_to_inject, underlying, profile, priority, scope, dependencies, bindings)
        self.prefix = prefix
        self.location = location
        self.override_properties = override_properties

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                ConfigurationPropertiesInjectTypeMetadata(self.ty_to_inject, self.underlying, p, self.priority,
                                                          self.scope, self.dependencies, self.bindings, self.prefix,
                                                          self.location, self.override_properties, )
                for p in self.profile
            ]


class ComponentFactoryInjectTypeMetadata(CallableFactory, InjectTypeMetadata):
    def __init__(self,
                 ty_to_inject: typing.Type[T],
                 underlying: typing.Type,
                 profile: typing.Union[str, list[str]],
                 priority: int,
                 scope: injector.ScopeDecorator,
                 dependencies: dict[str, ...],
                 bindings: list[typing.Type],
                 to_call: typing.Callable):
        InjectTypeMetadata.__init__(self, ty_to_inject, underlying, profile, priority,
                                    scope, dependencies, bindings)
        self._to_call = to_call

    @property
    def to_call(self) -> typing.Callable:
        return self._to_call

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                ComponentFactoryInjectTypeMetadata(self.ty_to_inject, self.underlying, p, self.priority,
                                                   self.scope, self.dependencies, self.bindings,
                                                   self._to_call)
                for p in self.profile
            ]


class ComponentSelfFactory(ComponentFactoryInjectTypeMetadata):

    def __init__(self, ty_to_inject: typing.Type[T], underlying: typing.Type, profile: typing.Union[str, list[str]],
                 priority: int, scope: injector.ScopeDecorator, dependencies: dict[str, ...],
                 bindings: list[typing.Type], to_call: typing.Union[typing.Callable, injector.CallableProvider]):
        super().__init__(ty_to_inject, underlying, profile, priority, scope, dependencies, bindings, to_call)

    @property
    def to_call(self) -> typing.Union[typing.Callable, injector.CallableProvider]:
        return self._to_call


class ComponentFactory(ComponentFactoryInjectTypeMetadata):

    @classmethod
    def new_component_factory(cls, cls_value, underlying, profile, priority, scope, bind_to):
        return ComponentFactory(cls_value, underlying, profile, priority, scope,
                                None, bind_to, None)



class BeanComponentFactory(ComponentFactoryInjectTypeMetadata):
    is_lazy: bool = False

    def __init__(self, ty_to_inject: typing.Type[T], underlying: typing.Type, profile: typing.Union[str, list[str]],
                 priority: int, scope: injector.ScopeDecorator, dependencies: dict[str, ...],
                 bindings: list[typing.Type], to_call: typing.Callable, is_lazy: bool = False):
        super().__init__(ty_to_inject, underlying, profile, priority, scope, dependencies, bindings, to_call)
        self.is_lazy = is_lazy

    @classmethod
    def new_bean_component_factory(cls, bean_ty: typing.Type[T], profile: str, priority: int,
                                   scope: injector.ScopeDecorator, factory: typing.Callable,
                                   lazy: bool = False):
        return BeanComponentFactory(
            bean_ty, bean_ty, profile, priority,
            scope, {}, [], factory,
            lazy
        )

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                BeanComponentFactory(self.ty_to_inject, self.underlying, p, self.priority,
                                     self.scope, self.dependencies, self.bindings,
                                     self._to_call, self.is_lazy)
                for p in self.profile
            ]


class LifecycleInjectTypeMetadata(InjectTypeMetadata, CallableFactory):

    def __init__(self, ty_to_inject: typing.Type[T], underlying: typing.Type, profile: typing.Union[str, list[str]],
                 priority: int, scope: injector.ScopeDecorator, dependencies: dict[str, ...],
                 bindings: list[typing.Type], lifecycle: LifeCycleHook, lifecycle_type: FnTy, to_call: typing.Callable,
                 args_callable: typing.Callable[[], dict[str, ...]] = None):
        super().__init__(ty_to_inject, underlying, profile, priority, scope, dependencies, bindings)
        self.args_callable = args_callable
        self._to_call = to_call
        self.lifecycle_type = lifecycle_type
        self.lifecycle = lifecycle

    @property
    def to_call(self) -> typing.Callable:
        return self._to_call

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                LifecycleInjectTypeMetadata(self.ty_to_inject, self.underlying, p, self.priority,
                                            self.scope, self.dependencies, self.bindings,
                                            self.lifecycle, self.lifecycle_type, self._to_call,
                                            self.args_callable)
                for p in self.profile
            ]


class PrototypeFactory(abc.ABC):
    @abc.abstractmethod
    def create(self, profile: typing.Optional[str] = None, **kwargs):
        pass
