import dataclasses
import enum
import functools
import typing

import injector

import python_util.reflection.reflection_utils
from python_di.env.base_env_properties import DEFAULT_PROFILE
from python_di.inject.injector_provider import InjectionContextInjector
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_util.logger.logger import LoggerFacade


class InjectionType(enum.Enum):
    Property = enum.auto()
    Dependency = enum.auto()
    Provided = enum.auto()


@dataclasses.dataclass(init=True)
class InjectionDescriptor:
    injection_ty: InjectionType
    scope: typing.Optional[injector.ScopeDecorator] = None
    profile: typing.Optional[str] = None
    dep_kwargs: dict = None
    skip_if_optional: bool = False

    @classmethod
    def skip_if_optional_descr(cls):
        return InjectionDescriptor(InjectionType.Provided, skip_if_optional=True)

    def get_scope(self) -> injector.ScopeDecorator:
        if self.scope is not None:
            return self.scope
        else:
            return injector.singleton

    def get_profile(self) -> str:
        if self.profile is not None:
            return self.profile
        else:
            return DEFAULT_PROFILE


@inject_context_di()
def retrieve_descriptor(value: typing.Union[typing.Type, str],
                        key: typing.Optional[str] = None,
                        default_value: typing.Optional = None,
                        scope_decorator: injector.ScopeDecorator = None,
                        profile: str = None,
                        injection_descriptor: typing.Optional[InjectionDescriptor] = None,
                        ctx: typing.Optional[InjectionContextInjector] = None):
    if injection_descriptor is None:
        if scope_decorator is None:
            scope_decorator = injector.singleton
        return ctx.get_interface(value, profile=profile, scope=scope_decorator)
    if injection_descriptor.skip_if_optional and 'Optional' in str(value):
        return None
    if injection_descriptor.injection_ty == InjectionType.Property:
        assert value == str or value == typing.Optional[str]
        assert key is not None
        if injection_descriptor.get_profile() is not None:
            profile = injection_descriptor.get_profile()
        return ctx.get_property_with_default(key, default_value, profile)
    else:
        assert injection_descriptor.injection_ty == InjectionType.Dependency
        if injection_descriptor.get_profile() is not None:
            profile = injection_descriptor.get_profile()
        if injection_descriptor.get_scope() is not None:
            scope_decorator = injection_descriptor.get_scope()
        return ctx.get_interface(value, profile=profile, scope=scope_decorator)


def autowire_fn(descr: dict[str, InjectionDescriptor] = None,
                scope_decorator: injector.ScopeDecorator = None,
                profile: str = None):
    """
    Wrap the function that needs values from the context. If the first argument in the decorated function is of
    type ConfigType, then the injected arguments will use this profile to retrieve the dependencies.
    :param profile:
    :param scope_decorator:
    :param descr:
    :param ctx:
    :return:
    """
    def wrapper(fn):
        def inject_proxy(*args, **kwargs):
            inject_proxy.wrapped_fn = fn
            args_to_call = {}
            profile_found, scope_decorator_found, config_type = _retrieve_scope_data(args, kwargs, fn)

            for i, k_v in enumerate(python_util.reflection.reflection_utils.get_all_fn_param_types(fn).items()):
                fn_arg_key = k_v[0]
                ty_default_tuple = k_v[1]
                ty_value_reflected = ty_default_tuple[0]
                default_value = ty_default_tuple[1]
                if i < len(args) and args[i] is not None:
                    args_to_call[fn_arg_key] = args[i]
                elif fn_arg_key in kwargs.keys() and kwargs[fn_arg_key] is not None:
                    args_to_call[fn_arg_key] = kwargs[fn_arg_key]
                elif ty_value_reflected is not None:
                    args_to_call[fn_arg_key] = retrieve_descriptor(ty_value_reflected, fn_arg_key, default_value,
                                                                   scope_decorator_found, profile_found,
                                                                   descr[fn_arg_key]
                                                                   if descr is not None and fn_arg_key in descr.keys()
                                                                   else None)
                elif default_value is None:
                    LoggerFacade.error("Found autowire fn with arg that has no default value, no value provided, and "
                                       "no type to inject from.")
            try:
                return fn(**args_to_call)
            except Exception as e:
                LoggerFacade.error(f"Error: {e}")
                raise e

        @inject_context_di()
        def _config_type(ctx: typing.Optional[InjectionContextInjector] = None):
            from drools_py.configs.config import ConfigType
            return ctx.get_interface(ConfigType)

        def _retrieve_scope_data(args, kwargs, fn) -> (str, injector.ScopeDecorator, ...):
            config_type, profile_scope_created = _get_profile_data(args, kwargs)

            if config_type is None:
                from drools_py.configs.config import ConfigType
                if any([ConfigType.__name__ in str(v) for k, v
                        in python_util.reflection.reflection_utils.get_all_fn_param_types(fn).items()]):
                    config_type = _config_type()
                    profile_scope_created = profile_scope

            if profile_scope_created is not None:
                scope_decorator_found = profile_scope_created
            else:
                scope_decorator_found = scope_decorator

            if config_type is not None:
                profile_found = config_type.value.lower()
            else:
                profile_found = profile
            return profile_found, scope_decorator_found, config_type

        return inject_proxy

    def _get_profile_data(args, kwargs) -> (object, injector.ScopeDecorator):
        config_type = None
        from drools_py.configs.config import ConfigType
        for a in args:
            if isinstance(a, ConfigType):
                config_type = a
        for a in kwargs.values():
            if isinstance(a, ConfigType):
                config_type = a

        return config_type, profile_scope if config_type is not None else None

    return wrapper

