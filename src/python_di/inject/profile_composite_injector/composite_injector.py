import asyncio
import threading
import typing
from typing import Union, Iterable

import injector
from injector import T, Provider, InstanceProvider, ScopeDecorator

from python_di.env.profile import Profile
from python_di.inject.profile_composite_injector.scopes.composite_scope import CompositeScope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope
from python_util.logger.logger import LoggerFacade



profile_scope = injector.ScopeDecorator(ProfileScope)
composite_scope = CompositeScope

CompositeInjectorT = typing.ForwardRef("CompositeInjectorT")
InjectionScopeT = typing.Union[typing.Type[injector.Scope], injector.ScopeDecorator]
ScopeTypeT = typing.TypeVar("ScopeTypeT")


class CompositeInjector(injector.Injector):

    def __init__(
            self,
            modules: Union[injector._InstallableModuleType, Iterable[injector._InstallableModuleType]] = None,
            auto_bind: bool = False,
            parent: injector.Injector = None,
            scope: typing.Optional[CompositeScope] = None,
            profile: typing.Union[Profile, None, ProfileScope] = None,
            *args,
            **kwargs,
    ):
        super().__init__(modules, auto_bind, parent)
        self.immutable = asyncio.Event()
        self.binder = injector.Binder(self, auto_bind=auto_bind, parent=parent.binder if parent is not None else None)
        self.binder.bind(injector.Injector, to=self)
        self.binder.bind(injector.Binder, to=self.binder)

        if isinstance(profile, ProfileScope):
            self.profile_scope = profile
        else:
            self.profile_scope = self._profile_scope(profile, parent)

        self.composite_created = self._composite_scope(parent, scope)

        self.parent = parent

        if not modules:
            modules = []
        elif not hasattr(modules, '__iter__'):
            modules = [modules]
            modules = modules

        # Initialise modules
        for module in modules:
            self.binder.install(module)

    def bind(self, interface: typing.Type[T], provider: Provider[T], scope: InjectionScopeT):
        assert not self.is_immutable(), "Was not immutable!"
        self.binder.bind(interface, provider, scope)

    def multibind(self, interface: typing.Type[T], provider: typing.Any, scope: InjectionScopeT):
        assert not self.is_immutable(), "Was not immutable!"
        self.binder.multibind(interface, to=provider, scope=scope)

    def create_child_injector(self, other: CompositeInjectorT, *args: typing.Any,
                              **kwargs: typing.Any) -> CompositeInjectorT:
        other: CompositeInjector = other
        other_child: CompositeInjector = other._create_child_injector(*args, **kwargs)
        other_child._collapse_parent()
        other_child.parent = self
        self._merge_bindings_static(other_child, self)
        other_child.get(injector.SingletonScope).injector = other_child
        return other_child

    def _profile_scope(self, profile: Profile, parent: injector.Injector):
        if profile is not None:
            if parent is not None and ProfileScope in parent.binder._bindings.keys():
                profile_scope = parent.get(ProfileScope)
                if profile_scope.profile == profile:
                    self.profile_scope = profile_scope
                    self.bind(ProfileScope, injector.InstanceProvider(self.profile_scope), ScopeDecorator(ProfileScope))
                    return self.profile_scope
            self.profile_scope = ProfileScope(self, profile)
            self.bind(ProfileScope, injector.InstanceProvider(self.profile_scope), ScopeDecorator(ProfileScope))
            self.profile_scope._context[ProfileScope] = InstanceProvider(self.profile_scope)
            return self.profile_scope

    def _composite_scope(self, parent, scope):
        if scope is None:
            if parent is None or (isinstance(parent, CompositeInjector) and parent.composite_created is None):
                self.composite_created = CompositeScope(self)
                if parent is not None:
                    self.fill_scope_with_bindings(parent.binder)
                self.binder.bind(injector.SingletonScope, self.composite_created, scope=injector.singleton)
                self.binder.bind(CompositeScope, self.composite_created, scope=injector.singleton)
            elif parent is not None and isinstance(parent, CompositeInjector) and parent.composite_created is not None:
                assert isinstance(parent, CompositeInjector), "Was not composite injector."
                self.composite_created = parent.composite_created
        else:
            self.composite_created = scope
            self.binder.bind(injector.SingletonScope, self.composite_created, scope=injector.singleton)
            self.binder.bind(CompositeScope, self.composite_created, scope=injector.singleton)
        return self.composite_created

    def fill_scope_with_bindings(self, binder):
        if binder is not None:
            from python_di.inject.profile_composite_injector.inject_utils import is_singleton_scope
            self.composite_created._context = {
                b_key: b for b_key, b in binder._bindings.items()
                if is_singleton_scope(b)
            }

    def _collapse_parent(self):
        """
        Collapse parent should only be called when the parent is no longer available for changes.
        :return:
        """
        if self.parent is not None:
            if isinstance(self.parent, CompositeInjector):
                assert not self.parent.is_immutable(), \
                    ("Attempted to collapse parent that was already collapsed. If this collapse was allowed, then "
                     "changes to the parent would not be reflected in the context.")
                self.parent._collapse_parent()
                self.parent.mark_immutable()
            elif self.parent.parent is not None:
                self.merge_parent(self.parent, self.parent.parent)
            self._merge_bindings_static(self, self.parent)
            self.parent = None

    def _create_child_injector(self, *args: typing.Any, **kwargs: typing.Any) -> CompositeInjectorT:
        child_injector = CompositeInjector(parent=self, scope=self.composite_created, *args, **kwargs)
        return child_injector

    def merge_parent(self, curr, curr_parent):
        if curr_parent.current is not None:
            self.merge_parent(curr_parent, curr_parent.current)
            self._merge_bindings_static(curr_parent, curr_parent.current)
        self._merge_bindings_static(curr, curr_parent)

    @classmethod
    def _merge_bindings_static(cls, to_merge_into: CompositeInjectorT,
                               to_merge_from: CompositeInjectorT):
        from python_di.inject.profile_composite_injector.inject_utils import is_singleton_scope
        to_merge_into: CompositeInjector = to_merge_into
        to_merge_from: CompositeInjector = to_merge_from
        cls.do_merge_scope(to_merge_from, to_merge_into)
        for binding_key, binding_found in to_merge_from:
            if binding_key != injector.Injector and binding_key != injector.Binder and binding_key != ProfileScope:
                from python_di.inject.prioritized_injectors import do_injector_bind
                if binding_key not in to_merge_into.binder._bindings.keys():
                    do_injector_bind(binding_found.interface, to_merge_into, binding_found.provider,
                                     binding_found.scope)
                elif is_singleton_scope(binding_found):
                    do_injector_bind(binding_found.interface, to_merge_into, binding_found.provider,
                                     binding_found.scope)
            elif binding_key == ProfileScope and to_merge_into.profile_scope is not None:
                from python_di.inject.prioritized_injectors import do_injector_bind
                if to_merge_from.profile_scope.profile == to_merge_into.profile_scope.profile:
                    for c, v in to_merge_into.profile_scope._context.items():
                        if c not in to_merge_from.profile_scope._context.keys():
                            to_merge_into.profile_scope._context[c] = v

        return to_merge_into

    @classmethod
    def do_merge_scope(cls, to_merge_from, to_merge_into):
        to_merge_into_singleton: injector.SingletonScope = cls.get_scope_type(to_merge_into, injector.SingletonScope)
        to_merge_from_singleton: injector.SingletonScope = cls.get_scope_type(to_merge_from, injector.SingletonScope)

        if to_merge_from_singleton is None and to_merge_into_singleton is not None:
            to_merge_from.binder.bind(injector.SingletonScope, to_merge_into_singleton, injector.singleton)
        elif to_merge_into_singleton is None and to_merge_from_singleton is not None:
            to_merge_into.binder.bind(injector.SingletonScope, to_merge_from_singleton, injector.singleton)
        elif to_merge_into_singleton is not None:

            if to_merge_from_singleton != to_merge_into_singleton:
                for c, v in to_merge_into_singleton._context.items():
                    if c not in to_merge_from_singleton._context.keys():
                        to_merge_from_singleton._context[c] = v

            to_merge_into.binder.bind(injector.SingletonScope, to_merge_from_singleton, injector.singleton)
            to_merge_into.binder.bind(CompositeScope, to_merge_from_singleton, injector.singleton)

    @classmethod
    def get_scope_type(cls, to_merge_from, scope_type: typing.Type[ScopeTypeT]):
        try:
            if isinstance(to_merge_from, CompositeInjector) and to_merge_from.composite_created is not None:
                return to_merge_from.composite_created
            else:
                found_scope_type = to_merge_from.get(scope_type, scope_type)
                return found_scope_type
        except Exception as e:
            LoggerFacade.error(e)

    def iter_bindings(self):
        yield from self.binder._bindings.items()

    def mark_immutable(self):
        self.immutable.set()

    def is_immutable(self):
        return self.immutable.is_set()

    def __contains__(self, item: typing.Type[T]):
        is_in_binding_keys = item in self.binder._bindings.keys()
        is_in_composite = item in self.composite_created._context.keys()
        return (is_in_binding_keys or is_in_composite)
        # or item in self.composite_created.injector.binder._bindings.keys())

    def __iter__(self):
        yield from self.iter_bindings()
