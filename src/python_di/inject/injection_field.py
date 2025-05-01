import asyncio
import typing

import injector

from python_di.inject.profile_composite_injector.composite_injector import CompositeInjector
from python_di.inject.profile_composite_injector.scopes.composite_scope import CompositeScope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope

T = typing.TypeVar("T")


def merge_injectors_with(injector_to_merge: CompositeInjector, injectors_to_merge: list[CompositeInjector]):
    for next_parent_injector in injectors_to_merge:
        injector_to_merge = injector_to_merge.create_child_injector(next_parent_injector)
    return injector_to_merge


class InjectionObservationField:
    """
    Allows for the registration of the dependencies for a profile per config, and then collapsing them into one
    CompositeInjector when the injector is retrieved by prioritized injectors.
    """

    def __init__(self, injectors: list[CompositeInjector] = None,
                 config_injectors: dict[typing.Type, list[CompositeInjector]] = None,
                 profile_scope: typing.Optional[ProfileScope] = None,
                 composite_scope: typing.Optional[CompositeScope] = None):
        """
        :param injectors:
        :param config_injectors:
        :param profile_scope:
        :param composite_scope:
        """

        self.composite_scope = composite_scope
        self.profile_scope = profile_scope
        self.config_injectors = config_injectors if config_injectors is not None else {}
        self.config_injector_ordering: list[typing.Type] = [i for i in self.config_injectors.keys()
                                                            if self.config_injectors is not None]
        self.injectors = injectors if injectors is not None else []
        self.collapsed: typing.Optional[CompositeInjector] = None
        self.profile_injector: typing.Optional[CompositeInjector] = None
        self.registered_event: asyncio.Event = asyncio.Event()

    def register_injector(self, to_register: CompositeInjector):
        self.injectors.append(to_register)
        self.registered_event.clear()

    def register_config_injector(self, composite_inj: CompositeInjector, new_ty: typing.Type):
        self.registered_event.clear()
        if new_ty in self.config_injectors.keys():
            self.config_injectors[new_ty].append(composite_inj)
        else:
            self.config_injector_ordering.append(new_ty)
            self.config_injectors[new_ty] = [composite_inj]

    def collapse_injectors(self):
        if not self.registered_event.is_set():
            if len(self) == 0:
                self.registered_event.set()
                return
            if len(self.config_injectors) == 0 and len(self.injectors) != 0:
                self.registered_event.set()
                if len(self.injectors) > 1:
                    i = self.injectors[0]
                    self.injectors = [self._collapse_injectors(i, self.injectors[1:], self.profile_scope,
                                                               self.composite_scope)]
                    self.bind_scopes(self.injectors[0])
                self.bind_scopes(self.injectors[0])
            elif len(self.config_injectors) != 0:
                self.registered_event.set()
                for config_ty in self.config_injector_ordering:
                    self._collapse_config_injector_ty(config_ty)
                self._collapse_config_to_collapse()
                if len(self.injectors) != 0:
                    self._collapse_injectors(self.collapsed, self.injectors, self.profile_scope, self.composite_scope)
                    self.injectors.clear()
                self.bind_scopes(self.collapsed)

        return self._retrieve_injector_inner()

    def bind_scopes(self, to_bind):
        self.bind_scopes_static(to_bind, self.profile_scope, self.composite_scope)

    @classmethod
    def bind_scopes_static(cls, to_bind, profile_scope, composite_scope):
        to_bind.binder.bind(ProfileScope, profile_scope, injector.ScopeDecorator(ProfileScope))
        profile_scope.injector = to_bind
        to_bind.binder.bind(CompositeScope, composite_scope, injector.singleton)

    def _collapse_config_to_collapse(self):
        is_all_one = all([len(c) == 1 for c in self.config_injectors.values()])
        assert is_all_one
        first_value = self.config_injector_ordering[0]
        to_collapse = self.config_injectors[first_value][0]
        to_merge_with = [config_injector for o in self.config_injector_ordering[1:]
                         for config_injector in self.config_injectors[o]]
        if len(to_merge_with) != 0:
            to_collapse = self._collapse_injectors(to_collapse, to_merge_with, self.profile_scope, self.composite_scope)
        self.config_injector_ordering = [first_value]
        self.config_injectors = {first_value: [to_collapse]}
        self.collapsed = to_collapse

    def _collapse_config_injector_ty(self, ty: typing.Type):
        c = self.config_injectors[ty]
        if len(c) == 1:
            collapsed = self._collapse_injectors(c[0], self.injectors, self.profile_scope, self.composite_scope)
            self.injectors.clear()
            self.config_injectors[ty] = [collapsed]
            self.collapsed = collapsed
        elif len(c) > 1:
            first_value = c[0]
            first_value = self._collapse_injectors(first_value, c[1:], self.profile_scope, self.composite_scope)
            first_value = self._collapse_injectors(first_value, self.injectors, self.profile_scope,
                                                   self.composite_scope)
            self.injectors.clear()
            self.config_injectors[ty] = [first_value]
            self.collapsed = first_value

    @classmethod
    def _collapse_injectors(cls, i: CompositeInjector, to_collapse_with: list[CompositeInjector],
                            profile_scope, composite_scope):
        """
        :param i:
        :param to_collapse_with: collapsed injectors in the queue ordering. So first injector in list is processed
        first. The result of each iteration is the adding of the dependencies to i if they didn't already exist in i.
        """
        if not to_collapse_with or len(to_collapse_with) == 0:
            return i
        for n in to_collapse_with:
            i = i.create_child_injector(n)
        cls.bind_scopes_static(i, profile_scope, composite_scope)
        return i

    def retrieve_injector(self, do_collapse: bool = True):
        """
        Returns the collapsed injector. Clears the register event because assumed that retrieval will modify.
        :return:
        """
        if not self.registered_event.is_set() and do_collapse:
            self.collapse_injectors()
            self.registered_event.clear()
            return self._retrieve_injector_inner()
        else:
            return self._retrieve_injector_inner()

    def _retrieve_injector_inner(self):
        from python_di.env.main_profile import DEFAULT_PROFILE
        if self.profile_scope.profile.profile_name == DEFAULT_PROFILE:
            self.composite_scope.injector = self.collapsed if self.collapsed is not None else self.injectors[0]
            self.composite_scope.injector.composite_created = self.composite_scope
        return self.collapsed if self.collapsed is not None else self.injectors[0] if len(self.injectors) != 0 else None

    def contains_config_type(self, config_type: typing.Type):
        return config_type in self.config_injectors.keys()

    def __len__(self):
        return len(self.injectors) + len(self.config_injectors)

    def __contains__(self, item: typing.Type[T]):
        return any([
            item in value for value in self.injectors
        ])
