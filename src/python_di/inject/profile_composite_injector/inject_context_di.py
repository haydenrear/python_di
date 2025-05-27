import dataclasses
import enum
import functools
import inspect
import typing

import injector

from python_di.env.main_profile import DEFAULT_PROFILE
from python_di.inject.injector_provider import InjectionContextInjector
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_util.logger.logger import LoggerFacade
from python_util.reflection.reflection_utils import is_empty_inspect, is_optional_ty, get_all_fn_param_types


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
        LoggerFacade.info(f"Retrieving {value} with profile {profile}.")
        f = ctx.get_interface(value, profile=profile, scope=scope_decorator)
        return f
    if injection_descriptor.skip_if_optional and is_optional_ty(value):
        return None
    if injection_descriptor.injection_ty == InjectionType.Provided:
        return None
    if injection_descriptor.injection_ty == InjectionType.Property:
        assert value == str or value == typing.Optional[str]
        assert key is not None
        if injection_descriptor.get_profile() is not None:
            profile = injection_descriptor.get_profile()
        LoggerFacade.info(f"Retrieving {key} with profile {profile}.")
        return ctx.get_property_with_default(key, default_value, profile)
    else:
        assert injection_descriptor.injection_ty == InjectionType.Dependency
        if injection_descriptor.get_profile() is not None:
            profile = injection_descriptor.get_profile()
        if injection_descriptor.get_scope() is not None:
            scope_decorator = injection_descriptor.get_scope()
        LoggerFacade.info(f"Retrieving {value} with profile {profile}.")
        return ctx.get_interface(value, profile=profile, scope=scope_decorator)


def autowire_fn(descr: dict[str, InjectionDescriptor] = None,
                scope_decorator: injector.ScopeDecorator = None,
                profile: str = None,
                config_type=None):
    """
    Wrap the function that needs values from the context. If the first argument in the decorated function is of
    type ConfigType, then the injected arguments will use this profile to retrieve the dependencies.
    :param config_type:
    :param profile:
    :param scope_decorator:
    :param descr:
    :param ctx:
    :return:
    """

    def wrapper(fn):
        @functools.wraps(fn)
        def inject_proxy(*args, **kwargs):
            if config_type is not None and profile is not None and config_type.value.lower() != profile.lower():
                raise ValueError(f"Both {config_type} and {profile} were provided to autowire fn for {fn}, "
                                 f"using {config_type} profile.")
            args_to_call, profile_found, scope_decorator_found = _deconstruct_profile_args_data(args, kwargs)
            for i, k_v in enumerate(get_all_fn_param_types(fn).items()):
                default_value, fn_arg_key, ty_value_reflected = _deconstruct_fn_args_values(k_v)
                if i < len(args) and args[i] is not None:
                    args_to_call[fn_arg_key] = args[i]
                elif fn_arg_key in kwargs.keys() and kwargs[fn_arg_key] is not None:
                    args_to_call[fn_arg_key] = kwargs[fn_arg_key]
                elif (ty_value_reflected is not None and not is_empty_inspect(ty_value_reflected)
                      and not is_optional_ty(ty_value_reflected)):
                    try:
                        args_to_call[fn_arg_key] = retrieve_descriptor(ty_value_reflected, fn_arg_key, default_value,
                                                                       scope_decorator_found, profile_found,
                                                                       descr[fn_arg_key]
                                                                       if descr is not None and fn_arg_key in descr.keys()
                                                                       else None)
                    except Exception as e:
                        LoggerFacade.error(f"Error when attempting to get {fn_arg_key}: {ty_value_reflected} "
                                           f"for {kwargs} and {args}: {e}")
                        raise e
                elif default_value is None:
                    LoggerFacade.debug("Found autowire fn with arg that has no default value, no value provided, and "
                                       f"no type to inject from when autowiring for {fn}.")
                    args_to_call[fn_arg_key] = None
                if fn_arg_key not in args_to_call.keys():
                    args_to_call[fn_arg_key] = None

            try:
                return fn(**args_to_call)
            except Exception as e:
                LoggerFacade.error(f"Error: {e} inside of inject_context_di for {kwargs} and {args}.")
                raise e

        def _deconstruct_fn_args_values(k_v):
            fn_arg_key = k_v[0]
            ty_default_tuple = k_v[1]
            ty_value_reflected = ty_default_tuple[0]
            default_value = ty_default_tuple[1]
            return default_value, fn_arg_key, ty_value_reflected

        def _deconstruct_profile_args_data(args, kwargs):
            inject_proxy.wrapped_fn = fn
            args_to_call = {}
            profile_found, scope_decorator_found, config_type_found = _retrieve_scope_data(args, kwargs, config_type)
            LoggerFacade.debug(f"{profile_found} is profile found in autowire_fn.")
            return args_to_call, profile_found, scope_decorator_found

        @inject_context_di()
        def _get_injectable_config_type(ctx: typing.Optional[InjectionContextInjector] = None):
            from drools_py.configs.config import ConfigType
            return ctx.get_interface(ConfigType)

        def _retrieve_scope_data(args, kwargs, config_type_) -> (str, injector.ScopeDecorator, ...):
            config_type_created, profile_scope_created = _get_profile_data(
                args, kwargs, _create_get_config_ty(config_type_)
            )
            return (_create_get_profile_found(config_type_created),
                    _create_get_scope_decorator(profile_scope_created),
                    config_type_created)

        def _create_get_profile_found(config_type_created):
            if config_type_created is not None:
                profile_found = config_type_created.value.lower()
            else:
                profile_found = profile
            return profile_found

        def _create_get_scope_decorator(profile_scope_created):
            if profile_scope_created is not None:
                scope_decorator_found = profile_scope_created
            else:
                scope_decorator_found = scope_decorator
            return scope_decorator_found

        def _create_get_config_ty(config_type):
            if config_type is None:
                from drools_py.configs.config import ConfigType
                config_type_created = _get_injectable_config_type()
            else:
                config_type_created = config_type
            return config_type_created

        return inject_proxy

    def _get_profile_data(args, kwargs, config_type) -> (object, injector.ScopeDecorator):
        from drools_py.configs.config import ConfigType
        config_type_found = config_type
        if config_type is None:
            for a in args:
                if isinstance(a, ConfigType):
                    config_type_found = a
            for a in kwargs.values():
                if isinstance(a, ConfigType):
                    config_type_found = a

        return config_type_found, profile_scope if config_type is not None else None

    return wrapper
