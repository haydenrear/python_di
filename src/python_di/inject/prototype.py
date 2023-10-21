import abc
import dataclasses
import typing
from typing import Optional

import injector

import python_di
from python_di.configs.constants import DiUtilConstants
from python_di.configs.di_util import get_underlying, get_wrapped_fn
from python_di.env.base_env_properties import DEFAULT_PROFILE
from python_di.inject.composite_injector import PrototypeScopeDecorator, profile_scope, \
    prototype_scope_decorator_factory, prototype_scope as proto_scope
from python_di.inject.inject_context_di import inject_context_di
from python_di.inject.injector_provider import InjectionContext
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class BeanDependencyDescriptor:
    profile: typing.Optional[str] = None
    scope: typing.Optional[injector.ScopeDecorator] = None


def retrieve_wrapped_factory_fn(cls) -> typing.Optional[typing.Tuple]:
    for k, v in cls.__dict__.items():
        if hasattr(v, DiUtilConstants.wrapped_fn.name) and hasattr(v.wrapped_fn, 'prototype_factory_fn'):
            return get_wrapped_fn(v)


def prototype_factory(profile: typing.Optional[str] = None,
                      prototype_decorator: typing.Optional[PrototypeScopeDecorator] = None,
                      dep_bean_scopes: dict[str, injector.ScopeDecorator] = None,
                      dep_bean_profiles: dict[str, str] = None):
    """
    Create a prototype factory out of the function. The bean_dep_scopes matches the arg names to the scopes for these
    args, and the same for the dep_bean_profiles. They can be None.
    :param profile: The profile to use as backup if no profile is provided for a dep.
    :param prototype_decorator: The particular prototype scope decorator (prototype scope decorator provided for each
    profile and then for singleton "profile". This can be left blank if profile is provided.
    :param dep_bean_scopes: The scope for each of the kwarg deps. Needed because python doesn't provide a way to
    add annotations to parameters.
    :param dep_bean_profiles: The profile for which to get the dep associated with key in dict.
    :return:
    """

    def factory_wrapper(fn):
        fn, wrapped = get_wrapped_fn(fn)
        fn.prototype_factory_fn = {}
        set_bean_dep_scope(fn)
        set_bean_dep_profile(fn)
        fn.profile = profile
        fn.prototype_decorator = prototype_decorator
        return fn

    def set_bean_dep_profile(fn):
        if dep_bean_profiles is not None:
            for k, v in dep_bean_profiles.items():
                if k in fn.prototype_factory_fn.keys():
                    fn.prototype_factory_fn[k].profile = v
                else:
                    fn.prototype_factory_fn[k] = BeanDependencyDescriptor(profile=v)

    def set_bean_dep_scope(fn):
        if dep_bean_scopes is not None:
            for k, v in dep_bean_scopes.items():
                if k in fn.prototype_factory_fn.keys():
                    fn.prototype_factory_fn[k].scope = v
                else:
                    fn.prototype_factory_fn[k] = BeanDependencyDescriptor(scope=v)

    return factory_wrapper


def retrieve_bean_scope_from_prototype(
        bean,
        profile: typing.Optional[str] = None
) -> typing.Optional[injector.ScopeDecorator]:
    bean_wrapped = retrieve_wrapped_factory_fn(bean)
    if bean_wrapped is not None:
        bean, _ = bean_wrapped
        if bean.prototype_decorator is not None:
            return bean.prototype_decorator
        if bean.profile is not None:
            return prototype_scope_decorator_factory(bean.profile)()
        else:
            return prototype_scope_decorator_factory(profile)()


class PrototypeFactory(abc.ABC):
    @abc.abstractmethod
    def create(self, profile: typing.Optional[str] = None, **kwargs):
        pass


@dataclasses.dataclass
class PrototypeComponentFactory:
    wrapped_fn: typing.Callable
    fn_arg_types: dict[str, typing.Type]
    profile: typing.Optional[str]
    prototype_decorator: typing.Optional[PrototypeScopeDecorator]
    factory: typing.Type[PrototypeFactory]
    cls_value: typing.Type


@inject_context_di()
def register_prototype_component_factory(component_factory_data: PrototypeComponentFactory,
                                         ctx: Optional[InjectionContext] = None):
    LoggerFacade.info(f"Registering {component_factory_data.cls_value} as prototype scope.")
    ctx.register_component(component_factory_data.factory,
                           [typing.cast(typing.Type, component_factory_data.factory)],
                           # register the factory as singleton, as each bean dep can be in a different scope.
                           injector.singleton)


def prototype_scope(cls):
    underlying = get_underlying(cls)
    prototype_self = cls

    class PrototypeFactoryProxy(PrototypeFactory):

        @classmethod
        def create(cls, profile: typing.Optional[str] = None, **kwargs):
            wrapped_values = retrieve_wrapped_factory_fn(underlying)
            assert wrapped_values is not None
            wrapped_fn, wrapped_values = wrapped_values

            bean_scopes, construct_values, prototype_decorator \
                = cls.get_bean_factory_data(kwargs, wrapped_fn, wrapped_values)

            for to_get_key, to_get_value in wrapped_values.items():
                bean_descr = cls.get_bean_descr(bean_scopes, to_get_key)

                bean_profile = cls.get_bean_profile(bean_descr, prototype_decorator, profile)
                construct_values[to_get_key] = cls.get_bean_dependency(
                    to_get_value,
                    bean_scope=cls.retrieve_bean_scope_item(bean_descr, prototype_decorator, bean_profile,
                                                            to_get_value),
                    profile=bean_profile,
                )

            if prototype_self.__init__ == wrapped_fn:
                return prototype_self(**construct_values)
            else:
                created = wrapped_fn(**construct_values)
                return created

        @classmethod
        def get_bean_descr(cls, bean_scopes, to_get_key):
            if to_get_key in bean_scopes.keys():
                bean_scope: Optional[BeanDependencyDescriptor] = bean_scopes[to_get_key]
            else:
                bean_scope: Optional[BeanDependencyDescriptor] = None
            return bean_scope

        @classmethod
        def retrieve_bean_scope_item(cls, bean_scope, prototype_decorator, create_profile, to_get_value):
            scope_decorator = retrieve_bean_scope_from_prototype(to_get_value, create_profile)
            if scope_decorator is not None:
                return scope_decorator
            if bean_scope is not None and bean_scope.scope is not None:
                bean_scope_item = bean_scope.scope
            elif create_profile is not None:
                bean_scope_item = injector.singleton \
                    if create_profile == DEFAULT_PROFILE \
                    else profile_scope
            elif prototype_decorator is not None:
                bean_scope_item = injector.singleton \
                    if prototype_decorator.profile == DEFAULT_PROFILE \
                    else profile_scope
            else:
                bean_scope_item = injector.singleton

            return bean_scope_item

        @classmethod
        def get_bean_profile(cls, bean_scope, prototype_decorator, create_profile):
            profile = None
            if bean_scope is not None and bean_scope.profile is not None:
                profile = bean_scope.profile
            elif create_profile is not None:
                profile = create_profile
            elif prototype_decorator is not None:
                assert isinstance(prototype_decorator, PrototypeScopeDecorator)
                profile = prototype_decorator.profile

            return profile

        @classmethod
        def get_bean_factory_data(cls, kwargs, wrapped_fn, wrapped_values):
            construct_values = {}
            bean_scopes = wrapped_fn.prototype_factory_fn
            if bean_scopes is None:
                bean_scopes = {}
            for prov_key, prov_value in kwargs.items():
                # if the user provided a kwarg, then remove it. #TODO: check valid type.
                if prov_value is not None:
                    del wrapped_values[prov_key]
                construct_values[prov_key] = prov_value
            return bean_scopes, construct_values, wrapped_fn.prototype_decorator

        @classmethod
        @inject_context_di()
        def get_bean_dependency(cls, bean_ty: typing.Type, bean_scope: Optional[injector.ScopeDecorator] = None,
                                profile: Optional[str] = None, ctx: Optional[InjectionContext] = None):
            return ctx.get_interface(bean_ty, profile=profile, scope=bean_scope)

    fn_wrapped = retrieve_wrapped_factory_fn(underlying)
    if fn_wrapped is None:
        return cls
    else:
        fn, wrapped = fn_wrapped
        register_prototype_component_factory(PrototypeComponentFactory(
            fn, wrapped, fn.profile, fn.prototype_decorator,
            PrototypeFactoryProxy, underlying
        ))

    underlying.prototype_bean_factory_ty = PrototypeFactoryProxy

    return cls
