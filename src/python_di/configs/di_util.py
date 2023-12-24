import typing

from python_di.configs.constants import DiUtilConstants, FnTy
from python_util.reflection.reflection_utils import get_all_fn_param_types_no_default


def get_wrapped_fn(fn) -> typing.Tuple[typing.Callable, dict]:
    """
    :param fn: the function for which to get the wrapped fn.
    :return: The wrapped fn (proxied value) and a dictionary that contains a mapping from the arg key to the arg type
    for that function.
    """
    if hasattr(fn, DiUtilConstants.wrapped_fn.name):
        fn = getattr(fn, DiUtilConstants.wrapped_fn.name)
    else:
        fn.wrapped_fn = fn
    wrapped = retrieve_wrapped_fn_args(fn)
    return fn, wrapped


def retrieve_fn_ty(fn):
    if hasattr(fn, '__name__') and fn.__name__ == '__init__':
        return FnTy.init_method
    for i, v in get_all_fn_param_types_no_default(fn).items():
        if i == 'self':
            return FnTy.self_method
        elif i == 'cls':
            return FnTy.class_method

    return FnTy.static_method


def retrieve_wrapped_fn_args(fn):
    wrapped = {i: v for i, v in get_all_fn_param_types_no_default(fn).items()
               if i != 'self' and i != 'args' and i != 'kwargs'}
    return wrapped


def get_underlying(cls):
    if hasattr(cls, DiUtilConstants.proxied.name):
        return getattr(cls, DiUtilConstants.proxied.name)
    else:
        cls.proxied = cls
    return cls


def add_attr(underlying, to_add, name):
    if hasattr(underlying, name):
        to_add_values = getattr(underlying, name)
        if to_add_values is None:
            setattr(underlying, name, [to_add])
        else:
            to_add_values.append(to_add)
    else:
        setattr(underlying, name, [to_add])


def has_sub(underlying, tys):
    if not hasattr(underlying, DiUtilConstants.subs.name):
        return False
    else:
        return tys in underlying.subs


def get_sub(underlying, matches: typing.Callable) -> typing.Optional:
    if hasattr(underlying, DiUtilConstants.subs.name):
        for s in underlying.subs:
            if matches(s):
                return s
