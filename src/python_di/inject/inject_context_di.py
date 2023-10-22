import functools
import inspect
import typing

import injector

import python_util.reflection.reflection_utils
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


@inject_context_di()
def autowire_fn(ctx: typing.Optional[InjectionContext] = None):
    """
    Wrap the function that needs values from the context.
    :param ctx:
    :return:
    """
    def wrapper(fn):
        @functools.wraps(fn)
        def inject_proxy(*args, **kwargs):
            get_create_inject_context(fn)
            inject_proxy.wrapped_fn = fn
            args_to_call = {}
            for i, k_v in enumerate(python_util.reflection.reflection_utils.get_all_fn_param_types_no_default(fn).items()):
                k = k_v[0]
                v = k_v[1]
                if i < len(args) and args[i] is not None:
                    args_to_call[k] = args[i]
                elif k in kwargs.keys() and kwargs[k] is not None:
                    args_to_call[k] = kwargs[k]
                elif v is not None:
                    args_to_call[k] = ctx.get_interface(v, scope=injector.singleton)
            return fn(**args_to_call)

        return inject_proxy

    return wrapper
