import threading
import typing
from typing import Type

import injector
from injector import T, Provider, synchronized

prototype_scope_lock = threading.RLock()


class PrototypeScope(injector.Scope):

    def __init__(self, parent: injector.Scope, injector_value: injector.Injector):
        super().__init__(injector_value)
        self.parent = parent

    def get(self, key: Type[T], provider: Provider[T]) -> Provider[T]:
        raise NotImplementedError("Prototype scope beans are created using the factory.")


class PrototypeScopeDecorator(injector.ScopeDecorator):
    def __init__(self, profile: typing.Optional[str] = None):
        super().__init__(PrototypeScope)
        self._profile = profile

    @property
    def profile(self) -> str:
        if self._profile is None:
            from python_di.env.main_profile import DEFAULT_PROFILE
            self._profile = DEFAULT_PROFILE
        return self._profile

    def __eq__(self, other):
        if type(other) != PrototypeScopeDecorator or PrototypeScopeDecorator not in type(other).__bases__:
            return False
        return self.profile == other.profile

    def __hash__(self):
        return hash((self.profile, PrototypeScopeDecorator.__name__))


prototype_scope = PrototypeScopeDecorator()


def prototype_scope_decorator(
        profile: typing.Optional[str] = None
) -> PrototypeScopeDecorator:
    return prototype_scope_decorator_factory(profile)()


def prototype_scope_decorator_factory(
        profile: typing.Optional[str] = None
) -> typing.Callable[[], PrototypeScopeDecorator]:
    prototype_scope_decorators = {}
    if profile is not None:
        profile = profile.lower()

    @synchronized(prototype_scope_lock)
    def retrieve_prototype_scope_fn():
        nonlocal prototype_scope_decorators
        if profile is None:
            return prototype_scope
        if profile in prototype_scope_decorators.keys():
            return prototype_scope_decorators[profile]
        else:
            new_prototype_decorator = PrototypeScopeDecorator(profile)
            prototype_scope_decorators[profile] = new_prototype_decorator
            return new_prototype_decorator

    return retrieve_prototype_scope_fn
