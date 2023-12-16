import typing

import injector

from python_util.reflection.reflection_utils import is_type_instance_of

T = typing.TypeVar("T")


def is_multibindable(type_to_check: typing.Type[T]):
    return (is_type_instance_of(type_to_check, dict)
            or is_type_instance_of(type_to_check, set)
            or is_type_instance_of(type_to_check, list))

def _flatten_providers(binding):
    if isinstance(binding, injector.Provider):
        yield from _flatten_providers_inner(binding)
    else:
        for p in binding:
            yield from _flatten_providers(p)

def _flatten_providers_inner(p):
    if isinstance(p, injector.MultiBindProvider):
        for inner in p._providers:
            yield from _flatten_providers(inner)
    else:
        yield p
