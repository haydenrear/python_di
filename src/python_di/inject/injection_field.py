import asyncio
import typing

import injector

import python_util.reflection.reflection_utils
from python_di.inject.profile_composite_injector.composite_injector import CompositeInjector, ProfileScope, \
    CompositeScope, profile_scope, composite_scope
from python_di.inject.profile_composite_injector.multibind_util import flatten_providers
from python_util.logger.logger import LoggerFacade

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
        self.composite_multibind_registrar: dict[typing.Type, typing.List[typing.Type]] = {}

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

        self.collapse_register_multibind()

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
        from python_di.env.base_env_properties import DEFAULT_PROFILE
        if self.profile_scope.profile.profile_name == DEFAULT_PROFILE:
            self.composite_scope.injector = self.collapsed if self.collapsed is not None else self.injectors[0]
            self.composite_scope.injector.composite_created = self.composite_scope
        return self.collapsed if self.collapsed is not None else self.injectors[0] if len(self.injectors) != 0 else None

    def contains_config_type(self, config_type: typing.Type):
        return config_type in self.config_injectors.keys()

    def register_multibindable(self, in_collection_bindings: list[type], concrete, scope):
        for i in in_collection_bindings:
            self.register_multibind([concrete], typing.List[i], scope)

    def register_multibind(self, in_collection_bindings: list[type], concrete, scope):
        self._add_to_registrar(concrete, in_collection_bindings, self.composite_multibind_registrar)

    @staticmethod
    def _add_to_registrar(concrete, in_collection_bindings, registrar):
        if concrete in registrar.keys():
            for i in in_collection_bindings:
                if i not in registrar[concrete]:
                    LoggerFacade.info(f"Adding {i} to {concrete} as Multibindable Registration")
                    registrar[concrete].append(i)
        else:
            registrar[concrete] = in_collection_bindings

    def collapse_register_multibind(self):
        from python_di.env.base_env_properties import DEFAULT_PROFILE
        injector_created = self._retrieve_injector_inner()
        if len(self.composite_multibind_registrar) != 0:
            for concrete, in_collection_bindings in self.composite_multibind_registrar.items():
                scope = self.composite_scope if self.profile_scope.profile.profile_name == DEFAULT_PROFILE else self.profile_scope
                provider = self._get_provider(concrete, scope)
                if provider is not None:
                    finished = self._retrieve_finished(in_collection_bindings, injector_created, provider)
                    assert isinstance(provider, injector.MultiBindProvider)
                    injector_created.multibind(
                        concrete,
                        lambda: self._retrieve_val([i for i in in_collection_bindings if i not in finished], scope,
                                                   concrete),
                        scope=self.create_get_scope(scope))
                else:
                    if provider is None and len(in_collection_bindings) != 0:
                        LoggerFacade.info(f"Creating provider {provider} for {in_collection_bindings}")
                        injector_created.binder.multibind(concrete,
                                                          self._retrieve_val_curry(in_collection_bindings, scope,
                                                                                   concrete),
                                                          scope=self.create_get_scope(scope))
            self.composite_multibind_registrar.clear()

    def _retrieve_val_curry(self, bindings, scope, concrete):
        return lambda: self._retrieve_val(bindings, scope, concrete)

    def _retrieve_val(self, bindings, scope, concrete):
        if not self.registered_event.is_set():
            self.collapse_injectors()
        out_bindings = []
        for b in bindings:
            out_bindings.append(self.retrieve_injector().get(b, scope=self.create_get_scope(scope)))

        return out_bindings

    def create_get_scope(self, scope_item):
        if isinstance(scope_item, ProfileScope):
            return profile_scope
        elif isinstance(scope_item, CompositeScope):
            return composite_scope
        elif isinstance(scope_item, injector.SingletonScope):
            return injector.singleton
        return injector.singleton

    def _retrieve_finished(self, in_collection_bindings, injector_created, provider):
        finished = []
        for flattened_provider in flatten_providers(provider):
            for t in in_collection_bindings:
                self._mark_potential_provider_already_existing(finished, flattened_provider, injector_created, t)
        return finished

    @staticmethod
    def _mark_potential_provider_already_existing(finished, flattened_provider, injector_created, t):
        if isinstance(flattened_provider,
                      injector.ClassProvider) and t not in finished and t == flattened_provider._cls:
            finished.append(t)
        elif isinstance(flattened_provider, injector.InstanceProvider):
            found_created = flattened_provider.get(injector_created)
            if t not in finished and type(found_created) == t:
                finished.append(t)
        elif isinstance(flattened_provider, injector.CallableProvider):
            found_created = flattened_provider.get(injector_created)
            if t not in finished and type(found_created) == t:
                finished.append(t)
        elif isinstance(flattened_provider, injector.MultiBindProvider):
            LoggerFacade.info(f"{t} was not finished for {flattened_provider}.")

    @staticmethod
    def _get_provider(concrete, scope) -> injector.Provider:
        if hasattr(scope, '_context') and concrete in scope._context.keys():
            return scope._context[concrete]
        else:
            if concrete in scope.injector.binder._bindings.keys():
                binding = scope.injector.binder.get_binding(concrete)
                return binding[0].provider

    def __len__(self):
        return len(self.injectors) + len(self.config_injectors)

    def __contains__(self, item: typing.Type[T]):
        return any([
            item in value for value in self.injectors
        ])
