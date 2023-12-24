from typing import Optional

from python_di.configs.base_config import DiConfiguration
from python_di.configs.bean import BeanModule, retrieve_callable_provider
from python_di.configs.di_util import get_underlying, get_wrapped_fn
from python_di.configs.constants import DiUtilConstants
from python_di.inject.context_factory.context_factory import ConfigurationFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import BeanComponentFactory
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
                        b_2.bean_ty, b_2.bean_factory_provider.profile, b_2.bean_factory_provider.priority,
                        b_2.scope, self._call_value(b_2)
                    ) for b_2 in beans.descriptors()
                ]
                lazy_bean_component_factory = [
                    BeanComponentFactory.new_bean_component_factory(
                        b_1.bean_ty, b_1.bean_factory_provider.profile, b_1.bean_factory_provider.priority,
                        b_1.scope, self._call_value(b_1),
                        True
                    ) for b_1 in lazy_beans.descriptors()
                ]
                bean_component_factory.extend(lazy_bean_component_factory)
                self._inject_types = bean_component_factory

            @property
            def inject_types(self) -> list[BeanComponentFactory]:
                return self._inject_types

            def _call_value(self, b_11):
                return b_11.bean_factory_provider.value(self, b_11.bean_factory_provider.profile)

        cls.context_factory = [ClassConfiguration()]
        cls.configuration_context_factory = True

        return cls

    def register_beans(beans, lazy_beans, value, fallback_profile):
        for k, v in value:
            if hasattr(v, DiUtilConstants.wrapped_fn.name):
                callable_fn, wrapped = get_wrapped_fn(v)
                profile_found = retrieve_profile_if_exists(callable_fn, profile)
                if profile_found is None:
                    profile_found = fallback_profile
                scope = callable_fn.scope
                if hasattr(callable_fn, DiUtilConstants.is_bean.name):
                    _register_bean_inner(beans, lazy_beans, profile_found, scope, callable_fn, wrapped)
        LoggerFacade.info("Registered beans.")

    def _register_bean_inner(beans__, lazy_beans__, profile_found__, scope, v__, wrapped__):
        return_type = get_return_type_from_fn(v__)
        if hasattr(v__, DiUtilConstants.is_lazy.name):
            _register_bean(lazy_beans__, profile_found__, return_type, scope, v__, wrapped__)
        else:
            _register_bean(beans__, profile_found__, return_type, scope, v__, wrapped__)

    def _register_bean(i_lazy_beans, profile_found_, return_type_, scope, v_, wrapped_):
        if profile_found_ is None:
            i_lazy_beans.register_bean(return_type_,
                                       retrieve_callable_provider(v_, profile_found_, wrapped_),
                                       scope)
        elif isinstance(profile_found_, str):
            i_lazy_beans.register_bean(return_type_,
                                       retrieve_callable_provider(v_, profile_found_, wrapped_),
                                       scope)
        elif isinstance(profile_found_, list):
            for p in profile_found_:
                i_lazy_beans.register_bean(return_type_,
                                           retrieve_callable_provider(v_, p, wrapped_),
                                           scope)
        else:
            LoggerFacade.error("Error - did not register.")

    def get_return_type_from_fn(v):
        return_type = get_return_type(v)
        if is_empty_inspect(return_type):
            if hasattr(v, DiUtilConstants.type_id.name):
                return v.type_id
        return return_type

    def retrieve_profile_if_exists(v, next_profile):
        if hasattr(v, DiUtilConstants.profile.name):
            return v.profile if v.profile is not None else next_profile

        return next_profile

    return class_decorator_inner


