import functools
import inspect
import typing

from python_di.inject.inject_context import inject_context
from python_di.inject.inject_utils import get_create_inject_context
from python_di.inject.injector_provider import InjectionContext
from python_util.reflection.reflection_utils import get_fn_param_types


def retrieve_ctx_arg(param_type: dict[str, (typing.Type, typing.Type)], fn):
    for param_name, param_type in param_type.items():
        if param_type[0] == typing.Optional[InjectionContext]:
            return param_name
    raise ValueError(f"Inject context DI was used on a function: {fn} that did not have a parameter of the type of the "
                     f"context.")


@inject_context()
def inject_context_di():
    """
    Decorator to provide the injection context
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
