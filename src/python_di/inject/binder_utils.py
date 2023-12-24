import typing

import injector

from python_di.inject.injector_provider import T, InjectionContextInjector
from python_di.inject.context_builder.inject_ctx import inject_context_di


def bind_multi_bind(multi_bind: typing.List[typing.Type[T]], binder: injector.Binder,
                    multi_bind_name: typing.Type[list[T]]):
    for to_bind in multi_bind:
        if to_bind not in binder._bindings.keys():
            binder.bind(to_bind, to_bind, scope=injector.singleton)
    if multi_bind_name not in binder._bindings.keys():
        binder.multibind(multi_bind_name, curry_multibind(multi_bind), scope=injector.singleton)


@inject_context_di()
def curry_multibind(multi_bind: typing.List[typing.Type[T]],
                    ctx: typing.Optional[InjectionContextInjector] = None):
    return lambda: [
        ctx.get_interface(to_bind, scope=injector.singleton) for to_bind in multi_bind
    ]
