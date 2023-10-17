import typing

import injector

from python_di.inject.composite_injector import CompositeScope
from python_di.inject.injector_provider import InjectionContext


def is_singleton_scope(binding: injector.Binding):
    scope = binding.scope
    if isinstance(scope, injector.ScopeDecorator):
        scope = scope.scope
    is_singleton = (isinstance(scope, injector.SingletonScope) or scope == injector.SingletonScope
                    or scope == CompositeScope)
    return is_singleton


def is_scope_singleton_scope(scope: typing.Union[injector.Scope, injector.ScopeDecorator, typing.Type]):
    if isinstance(scope, injector.ScopeDecorator):
        scope = scope.scope
    is_singleton = (isinstance(scope, injector.SingletonScope) or scope == injector.SingletonScope
                    or scope == CompositeScope)
    return is_singleton


def get_create_attr(fn, name, factory):
    if hasattr(fn, name):
        return getattr(fn, name)
    else:
        setattr(fn, name, factory)
        return getattr(fn, name)


def get_inject_context(fn):
    from python_di.configs.di_util import DiUtilConstants
    from python_di.configs.di_util import get_wrapped_fn
    fn, wrapped = get_wrapped_fn(fn)
    return getattr(fn, DiUtilConstants.inject_context.name)


def get_create_inject_context(fn):
    from python_di.configs.di_util import DiUtilConstants
    ctx = inject_context_abstract_factory()
    return get_create_attr(fn, DiUtilConstants.inject_context.name, lambda: ctx())


def inject_context_abstract_factory():
    inject_context: InjectionContext = InjectionContext

    def context():
        nonlocal inject_context
        return inject_context

    return context
