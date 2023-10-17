from python_di.inject.inject_utils import get_create_inject_context


def inject_context():
    """
    Decorator to provide the injection context
    :return:
    """
    def inject_proxy(fn):
        from python_di.configs.di_util import get_wrapped_fn
        fn, wrapped = get_wrapped_fn(fn)
        get_create_inject_context(fn)
        inject_proxy.wrapped_fn = fn
        return fn

    return inject_proxy


