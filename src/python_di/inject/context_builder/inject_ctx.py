import functools
import threading
import typing
from typing import Optional

import injector as injector

from python_di.configs.constants import DiUtilConstants
from python_di.inject.injector_provider import InjectionContextInjector
from python_util.reflection.reflection_utils import get_fn_param_types

set_injection_ctx_lock = threading.RLock()


def inject_context(injected_ctx: Optional[InjectionContextInjector] = None):
    if injected_ctx is not None:
        _set_inject_ctx(injected_ctx)

    def inject_proxy(fn):
        if injected_ctx is None:
            from python_di.configs.di_util import get_wrapped_fn
            fn, wrapped = get_wrapped_fn(fn)
            # must be a lambda because could change
            fn.inject_context = lambda: _retrieve_inject_ctx()
            inject_proxy.wrapped_fn = fn

        return fn

    def _retrieve_inject_ctx():
        assert hasattr(inject_context, DiUtilConstants.ctx.name), \
            "Attempted to access inject context before it was set."
        return inject_context.ctx

    return inject_proxy


@injector.synchronized(set_injection_ctx_lock)
def _set_inject_ctx(injected_ctx):
    inject_context.ctx = injected_ctx


def retrieve_ctx_arg(param_type: dict[str, (typing.Type, typing.Type)], fn):
    for param_name, param_type in param_type.items():
        if (param_type[0] == typing.Optional[InjectionContextInjector]
                or param_type[0] == InjectionContextInjector
                or param_type[0] == typing.Type[InjectionContextInjector]
                or param_name == 'ctx'):
            return param_name
    raise ValueError(f"Inject context DI was used on a function: {fn} that did not have a parameter of the type of the "
                     f"context.")


@inject_context()
def inject_context_di():
    """
    Decorator to provide the injection context.
    :return:
    """

    def wrapper(fn):
        @functools.wraps(fn)
        def inject_proxy(*args, **kwargs):
            inject_proxy.wrapped_fn = fn
            param_name = retrieve_ctx_arg(get_fn_param_types(fn), fn)
            kwargs[param_name] = inject_context_di.inject_context()
            return fn(*args, **kwargs)

        return inject_proxy

    return wrapper
