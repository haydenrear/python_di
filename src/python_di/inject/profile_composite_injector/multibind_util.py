import typing

import injector

from python_util.reflection.reflection_utils import is_type_instance_of

T = typing.TypeVar("T")


def is_multibindable(type_to_check: typing.Type[T]):
    return (is_type_instance_of(type_to_check, dict)
            or is_type_instance_of(type_to_check, set)
            or is_type_instance_of(type_to_check, list)
            or is_type_instance_of(type_to_check, injector.MultiBindProvider)
            or is_type_instance_of(type_to_check, injector.ListOfProviders))


def is_multibindable_provider(type_to_check: injector.Provider[T]):
    return isinstance(type_to_check, injector.MultiBindProvider) \
        or isinstance(type_to_check, injector.ListOfProviders)


def flatten_providers(binding):
    if isinstance(binding, injector.Provider):
        yield from _flatten_providers_inner(binding)
    else:
        for p in binding:
            yield from flatten_providers(p)


def _flatten_providers_inner(p):
    if isinstance(p, injector.MultiBindProvider):
        for inner in p._providers:
            yield from flatten_providers(inner)
    else:
        yield p
