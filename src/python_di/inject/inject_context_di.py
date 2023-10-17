import functools

from python_di.inject.inject_context import inject_context
from python_di.inject.inject_utils import get_create_inject_context


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
            kwargs['ctx'] = ctx
            return fn(*args, **kwargs)

        return inject_proxy

    return wrapper
