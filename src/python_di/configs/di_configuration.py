from typing import Optional

import injector

from python_di.configs.base_config import DiConfiguration
from python_di.configs.bean import BeanModule, retrieve_callable_provider, BeanArg
from python_di.configs.di_util import get_underlying, get_wrapped_fn
from python_di.configs.constants import DiUtilConstants
from python_di.inject.context_builder.ctx_util import set_add_context_factory
from python_di.inject.context_factory.context_factory import ConfigurationFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import BeanComponentFactory
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade
from python_util.reflection.reflection_utils import get_return_type, is_empty_inspect


def get_config_clzz(underlying):
    if hasattr(underlying, DiUtilConstants.subs.name):
        for s in underlying.subs:
            if DiConfiguration in s.__bases__:
                return s
    return underlying


def configuration(priority: Optional[int] = None, profile: Optional[str] = None):
    def class_decorator_inner(cls):
        underlying = get_underlying(cls)

        beans = BeanModule()
        lazy_beans = BeanModule()

        value = cls.__dict__.items()
        register_beans(beans, lazy_beans, value, profile)

        if cls != underlying:
            value = underlying.__dict__.items()
            register_beans(beans, lazy_beans, value, profile)

        class ClassConfiguration(ConfigurationFactory):

            def __init__(self):
                ConfigurationFactory.__init__(self, profile, priority, cls, underlying)
                bean_component_factory = [
                    BeanComponentFactory.new_bean_component_factory(
                        b_2.bean_ty, b_2.scope.profile, b_2.scope.priority,
                        b_2.scope.scope, self._call_value(b_2), bindings=b_2.scope.bindings
                    ) for b_2 in beans.descriptors()
                ]
                lazy_bean_component_factory = [
                    BeanComponentFactory.new_bean_component_factory(
                        b_1.bean_ty, b_1.scope.profile,
                        b_1.scope.priority,
                        b_1.scope.scope, self._call_value(b_1),
                        True, b_1.scope.bindings
                    ) for b_1 in lazy_beans.descriptors()
                ]
                bean_component_factory.extend(lazy_bean_component_factory)
                self._inject_types = bean_component_factory

            @property
            def inject_types(self) -> list[BeanComponentFactory]:
                return self._inject_types

            def _call_value(self, b_11):
                return b_11.bean_factory_provider.value(self, b_11.scope.profile)

        set_add_context_factory([ClassConfiguration()], cls)

        cls.configuration_context_factory = True

        return cls

    def register_beans(beans, lazy_beans, value, fallback_profile):
        for k, v in value:
            if hasattr(v, DiUtilConstants.wrapped_fn.name):
                callable_fn, wrapped = get_wrapped_fn(v)
                if hasattr(callable_fn, DiUtilConstants.is_bean.name):
                    for bean_arg_item in _retrieve_update_bean_arg(callable_fn, fallback_profile):
                        _register_bean_inner(beans, lazy_beans, bean_arg_item, callable_fn, wrapped)
        LoggerFacade.info("Registered beans.")

    def _retrieve_update_bean_arg(callable_fn, fallback_profile):
        from python_di.env.base_env_properties import DEFAULT_PROFILE
        bean_arg: BeanArg = callable_fn.is_bean
        profile_found = retrieve_profile_if_exists(bean_arg.profile, profile, fallback_profile)
        if profile_found is None:
            profile_found = DEFAULT_PROFILE
        scope = retrieve_scope_if_exists(
            bean_arg.scope,
            profile_scope if profile_found == DEFAULT_PROFILE
            else injector.singleton
        )
        bean_arg.scope = scope
        bean_arg.profile = profile_found
        if bean_arg.profile is None or isinstance(bean_arg.profile, str):
            yield bean_arg
        elif isinstance(bean_arg.profile, list):
            for p in bean_arg.profile:
                new_bean_arg = BeanArg(bean_arg.wrapped, p, bean_arg.priority, bean_arg.scope, bean_arg.bindings,
                                       bean_arg.self_factory)
                yield new_bean_arg

    def _register_bean_inner(beans__, lazy_beans__, bean_arg: BeanArg, v__, wrapped__):
        return_type = get_return_type_from_fn(v__)
        if hasattr(v__, DiUtilConstants.is_lazy.name):
            _register_bean(lazy_beans__, bean_arg, return_type, v__, wrapped__)
        else:
            _register_bean(beans__, bean_arg, return_type, v__, wrapped__)

    def _register_bean(i_lazy_beans, bean_arg: BeanArg, return_type_, v_, wrapped_):
        assert bean_arg.profile is None or isinstance(bean_arg.profile, str)
        i_lazy_beans.register_bean(return_type_,
                                   retrieve_callable_provider(v_, wrapped_, bean_arg),
                                   bean_arg)

    def get_return_type_from_fn(v):
        return_type = get_return_type(v)
        if is_empty_inspect(return_type):
            if hasattr(v, DiUtilConstants.type_id.name):
                return v.type_id
        return return_type

    def retrieve_scope_if_exists(scope_, next_scope, fallback_scope = injector.singleton):
        p = scope_ if scope_ is not None else next_scope
        if p is not None:
            return p
        return fallback_scope

    def retrieve_profile_if_exists(profile_, next_profile, fallback_):
        p = profile_ if profile_ is not None else next_profile
        if p is not None:
            return p
        return fallback_


    return class_decorator_inner


