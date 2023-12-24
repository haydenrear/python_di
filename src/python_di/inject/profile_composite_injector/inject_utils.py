import typing

import injector



def is_singleton_scope(binding: injector.Binding):
    scope = binding.scope
    if isinstance(scope, injector.ScopeDecorator):
        scope = scope.scope

    from python_di.inject.profile_composite_injector.composite_injector import CompositeScope
    is_singleton = (isinstance(scope, injector.SingletonScope) or scope == injector.SingletonScope
                    or scope == CompositeScope)
    return is_singleton


def is_scope_singleton_scope(scope: typing.Union[injector.Scope, injector.ScopeDecorator, typing.Type]):
    if isinstance(scope, injector.ScopeDecorator):
        scope = scope.scope
    from python_di.inject.profile_composite_injector.composite_injector import CompositeScope
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


