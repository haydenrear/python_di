import dataclasses
import enum
import functools
import inspect
import typing

import injector

import python_util.reflection.reflection_utils
from python_di.env.base_env_properties import DEFAULT_PROFILE
from python_di.inject.inject_context import inject_context
from python_di.inject.inject_utils import get_create_inject_context
from python_di.inject.injector_provider import InjectionContext
from python_util.reflection.reflection_utils import get_fn_param_types


def retrieve_ctx_arg(param_type: dict[str, (typing.Type, typing.Type)], fn):
    for param_name, param_type in param_type.items():
        if (param_type[0] == typing.Optional[InjectionContext]
                or param_type[0] == InjectionContext
                or param_type[0] == typing.Type[InjectionContext]):
            return param_name
    raise ValueError(f"Inject context DI was used on a function: {fn} that did not have a parameter of the type of the "
                     f"context.")


@inject_context()
def inject_context_di():
    """
    Decorator to provide the injection context.
    :return:
    """
    ctx = inject_context_di.inject_context()

    def wrapper(fn):
        @functools.wraps(fn)
        def inject_proxy(*args, **kwargs):
            get_create_inject_context(fn)
            inject_proxy.wrapped_fn = fn
            param_name = retrieve_ctx_arg(get_fn_param_types(fn), fn)
            kwargs[param_name] = ctx
            return fn(*args, **kwargs)

        return inject_proxy

    return wrapper


class InjectionType(enum.Enum):
    Property = enum.auto()
    Dependency = enum.auto()


@dataclasses.dataclass(init=True)
class InjectionDescriptor:
    injection_ty: InjectionType
    scope: typing.Optional[injector.ScopeDecorator] = None
    profile: typing.Optional[str] = None
    dep_kwargs: dict = None

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
                        injection_descriptor: typing.Optional[InjectionDescriptor] = None,
                        ctx: typing.Optional[InjectionContext] = None):
    if injection_descriptor is None:
        assert isinstance(value, typing.Type)
        return ctx.get_interface(value, scope=injector.singleton)
    if injection_descriptor.injection_ty == InjectionType.Property:
        assert value == str or value == typing.Optional[str]
        assert key is not None
        assert injection_descriptor is not None
        return ctx.get_property_with_default(key, default_value,
                                             injection_descriptor.get_profile(),
                                             **(injection_descriptor.dep_kwargs
                                                if injection_descriptor.dep_kwargs is not None
                                                else {}))
    else:
        assert injection_descriptor.injection_ty == InjectionType.Dependency
        assert isinstance(value, typing.Type)
        return ctx.get_interface(value, profile=injection_descriptor.get_profile(),
                                 scope=injection_descriptor.get_scope())



def autowire_fn(descr: dict[str, InjectionDescriptor] = None):
    """
    Wrap the function that needs values from the context.
    :param descr:
    :param ctx:
    :return:
    """

    def wrapper(fn):
        @functools.wraps(fn)
        def inject_proxy(*args, **kwargs):
            get_create_inject_context(fn)
            inject_proxy.wrapped_fn = fn
            args_to_call = {}
            for i, k_v in enumerate(
                    python_util.reflection.reflection_utils.get_all_fn_param_types(fn).items()):
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
                                                          descr[fn_arg_key] if descr is not None and fn_arg_key in descr.keys()
                                                          else None)
            return fn(**args_to_call)

        return inject_proxy

    return wrapper
