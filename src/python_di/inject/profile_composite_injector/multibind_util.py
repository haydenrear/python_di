import typing

import injector

from python_util.logger.logger import LoggerFacade
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


def multibind_idempotently(to_add, current_provider):
    pass


def retrieve_finished(in_collection_bindings, injector_created, provider):
    finished = []
    for flattened_provider in flatten_providers(provider):
        for t in in_collection_bindings:
            _mark_finished(finished, flattened_provider, injector_created, t)
    return finished


def _mark_finished(finished, flattened_provider, injector_created, t):
    if isinstance(flattened_provider,
                  injector.ClassProvider) and t not in finished and t != flattened_provider._cls:
        finished.append(t)
    elif isinstance(flattened_provider, injector.InstanceProvider):
        found_created = flattened_provider.get(injector_created)
        if t not in finished and type(found_created) != t:
            finished.append(t)
    elif isinstance(flattened_provider, injector.CallableProvider):
        found_created = flattened_provider.get(injector_created)
        if t not in finished and type(found_created) != t:
            finished.append(t)
    elif isinstance(flattened_provider, injector.MultiBindProvider):
        LoggerFacade.info(f"{t} was not finished for {flattened_provider}.")


def _get_provider(concrete, scope) -> injector.Provider:
    if hasattr(scope, '_context') and concrete in scope._context.keys():
        return scope._context[concrete]
    else:
        if concrete in scope.injector.binder._bindings.keys():
            binding = scope.injector.binder.get_binding(concrete)
            return binding[0].provider
