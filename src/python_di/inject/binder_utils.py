import typing

import injector

from python_di.inject.injector_provider import T, InjectionContextInjector
from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_di.inject.profile_composite_injector.scopes.composite_scope import CompositeScope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope


def bind_multi_bind(multi_bind: typing.List[typing.Type[T]], binder: injector.Binder,
                    multi_bind_name: typing.Type[list[T]], scope=injector.singleton):
    for to_bind in multi_bind:
        if to_bind not in binder._bindings.keys():
            binder.bind(to_bind, to_bind, scope=scope)
    if multi_bind_name not in binder._bindings.keys():
        binder.multibind(multi_bind_name, curry_multibind(multi_bind, scope), scope=scope)


@inject_context_di()
def curry_multibind(multi_bind: typing.List[typing.Type[T]],
                    scope=injector.singleton,
                    ctx: typing.Optional[InjectionContextInjector] = None):
    return lambda: [
        ctx.get_interface(to_bind, scope=scope) for to_bind in multi_bind
    ]


def is_singleton_composite(scope):
    scope = _get_scope(scope)

    if scope == injector.SingletonScope or scope == CompositeScope:
        return True
    return False


def _get_scope(scope):
    while isinstance(scope, injector.ScopeDecorator):
        scope = scope.scope
    return scope


def is_profile_scope(scope):
    scope = _get_scope(scope)

    if scope == ProfileScope:
        return True
    return False


def is_no_scope(scope):
    scope = _get_scope(scope)
    if scope == injector.NoScope:
        return True
    return False