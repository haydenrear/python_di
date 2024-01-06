import dataclasses
import functools
import typing
from typing import Optional

import injector

from python_di.configs.base_config import DiConfiguration
from python_di.configs.di_util import get_wrapped_fn
from python_di.env.base_env_properties import DEFAULT_PROFILE
from python_di.inject.context_factory.base_context_factory import CallableFactory
from python_di.inject.context_factory.type_metadata.base_ty_metadata import HasFnArgs
from python_di.inject.context_factory.context_factory_executor.metadata_factory import MetadataFactory
from python_di.inject.context_factory.context_factory_executor.register_factory import retrieve_factory
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class BeanArg:
    wrapped: ...
    profile: typing.Union[str, list[str], None]
    priority: typing.Optional[int]
    scope: Optional[injector.ScopeDecorator] = None
    bindings: list[typing.Type] = None
    self_factory: bool = False


def bean(profile: typing.Union[str, list[str], None] = None,
         priority: Optional[int] = None,
         self_factory: bool = False,
         scope: Optional[typing.Type[injector.Scope]] = None,
         bindings: list[typing.Type] = None):
    def bean_wrap(fn):
        fn, wrapped = get_wrapped_fn(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        fn.is_bean = BeanArg(wrapped, profile if profile is not None else DEFAULT_PROFILE, priority,
                             scope if scope is not None else injector.singleton,
                             bindings, self_factory)
        fn.wrapped = wrapped
        wrapper.wrapped_fn = fn

        return wrapper

    return bean_wrap


def lazy(fn):
    fn, wrapped = get_wrapped_fn(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.wrapped_fn = fn
    fn.is_lazy = True
    fn.wrapped = wrapped
    return wrapper


class BeanFactoryProvider:

    def __init__(self,
                 value: typing.Callable[[DiConfiguration, str], injector.CallableProvider]):
        self.value = value


T = typing.TypeVar('T')


@dataclasses.dataclass(init=True)
class BeanDescriptor:
    scope: BeanArg
    bean_ty: typing.Type[T]
    bean_factory_provider: BeanFactoryProvider


@dataclasses.dataclass(init=True)
class BeanCallableFactory(CallableFactory, HasFnArgs):
    _to_call: typing.Callable
    _fn_args: dict[str, type]

    @property
    def to_call(self) -> typing.Callable:
        return self._to_call

    @property
    def fn_args(self) -> dict[str, type]:
        return self._fn_args


class BeanModule:

    def __init__(self, beans: list[(typing.Type, BeanFactoryProvider, BeanArg)] = None):
        self.beans_builder: list[(typing.Type, BeanFactoryProvider, BeanArg)] = beans if beans is not None else []

    def register_bean(self, bean_ty: typing.Type, provider: BeanFactoryProvider, bean_arg: BeanArg):
        self.beans_builder.append((bean_ty, provider, bean_arg))

    def descriptors(self) -> list[BeanDescriptor]:
        return [
            BeanDescriptor(scope, bean_ty, factory_provider)
            for (bean_ty, factory_provider, scope) in self.beans_builder
        ]


def retrieve_callable_provider(v, wrapped, bean_arg: BeanArg) -> BeanFactoryProvider:
    return BeanFactoryProvider(_create_bean_factory_factory(v, wrapped, bean_arg))


def _create_bean_factory_factory(v, wrapped, bean_arg: BeanArg):
    return lambda config, profile_created: create_callable_provider_curry(
        v, bean_arg.profile, wrapped, config
    )


def create_callable_provider_curry(v, profile, wrapped, config):
    try:
        return injector.CallableProvider(lambda: get_value(v, profile, wrapped, config))
    except Exception as t:
        LoggerFacade.error(f"Received type error for {v.__class__.__name__}: {t}.")
        raise t


def get_value(v, profile, wrapped, config):
    return v(**create_callable_provider(v, wrapped, profile, config))


def create_callable_provider(v, wrapped, profile, config):
    do_inject, to_construct_factories = retrieve_factory(BeanCallableFactory(v, wrapped),
                                                         MetadataFactory(injectable_profile=profile))

    provider_created = to_construct_factories if to_construct_factories is not None else {}
    _set_config(wrapped, provider_created, profile)
    provider_created['self'] = config

    return provider_created


def _set_config(value, curr, p):
    if p is not None and value is not None:
        for k, v in value.items():
            from drools_py.configs.config import ConfigType
            if v == ConfigType:
                curr[k] = ConfigType.from_value(p)


def test_inject(profile: typing.Union[str, list[str], None] = None, priority: Optional[int] = None,
                type_id: Optional[str] = None, self_factory: bool = False,
                scope: Optional[typing.Type[injector.Scope]] = None):
    def test_inject_wrapped(fn):
        fn, wrapped = get_wrapped_fn(fn)

        fn.is_test_inject = True
        fn.profile = profile
        fn.priority = priority
        fn.wrapped = wrapped
        fn.type_id = type_id
        fn.scope = scope if scope is not None else injector.singleton
        fn.wrapped_fn = fn

        return fn

    return test_inject_wrapped
