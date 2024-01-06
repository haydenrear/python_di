from typing import Type

import injector
from injector import Provider, T

from python_di.env.profile import Profile
from python_util.logger.logger import LoggerFacade


class ProfileScope(injector.Scope):
    """
    Manages creation and context of objects.
    """
    _context = dict[type, Provider]

    def __init__(self, profile_level_injector: injector.Injector, profile: Profile):
        super().__init__(profile_level_injector)
        self._context = {}
        self.profile = profile

    def get(self, key: Type[T], provider: Provider[T] = None) -> Provider[T]:
        if key in self._context.keys():
            return self._context[key]
        else:
            # If fails, try to get from composite scope, which will get from the highest priority profile.
            try:
                provider = provider.get(self.injector)
                assert not isinstance(provider, injector.Provider)
                instance_provider = injector.InstanceProvider(provider)
            except Exception as e:
                if isinstance(e, AssertionError):
                    LoggerFacade.error(f"Found assertion error: {e}")
                    raise e
                if isinstance(provider, injector.ClassProvider):
                    cls_found = provider._cls
                    self._try_fix_bind_issue(cls_found.__init__)
                elif isinstance(provider, injector.CallableProvider):
                    callable_value = provider._callable
                    self._try_fix_bind_issue(callable_value)
                else:
                    LoggerFacade.error(f"Could not retrieve unsatisfied requirement: {e}. Unknown provider type "
                                       f"when trying to get from composite: {type(provider).__name__}")

                instance_provider = injector.InstanceProvider(provider.get(self.injector))

            self._context[key] = instance_provider
            return self._context[key]

    def _try_fix_bind_issue(self, provider):
        bindings_created = injector.get_bindings(provider)
        from python_di.inject.profile_composite_injector.scopes.composite_scope import CompositeScope
        retrieved_composite_scope = self.injector.get(CompositeScope, scope=injector.singleton)
        for binding_key, binding_ty in bindings_created.items():
            self._get_register_binding_dep_recursive(binding_ty, retrieved_composite_scope)

    def _get_register_binding_dep_recursive(self, binding_ty, retrieved_composite_scope):
        """
        Recursively climb the dependency tree if the binder does not exist. The composite scope is the ability to
        walk through the other ProfileScopes in order of precedence.
        :param binding_ty:
        :param retrieved_composite_scope:
        :return:
        """
        is_valid_dep = self._is_valid_dep(binding_ty)
        if is_valid_dep:
            if binding_ty not in self.injector.binder.bindings.keys() and is_valid_dep:
                self._context[binding_ty] = retrieved_composite_scope.get(binding_ty,
                                                                          injector.ClassProvider(binding_ty))
            elif binding_ty not in self._context.keys():
                # to prohibit infinite recursion, as the composite scope will inevitably ask this profile scope again.
                from python_di.inject.binder_utils import is_singleton_composite, is_profile_scope, is_no_scope
                # TODO: prohibit from creating no_scope binding that keeps it from searching through the other scopes.
                binding_found = self.injector.binder.get_binding(binding_ty)[0]
                if is_no_scope(binding_found.scope):
                    LoggerFacade.warn(f"Found no scope {binding_ty} in ProfileScope. Deleting it now.")
                    del self.injector.binder.bindings[binding_ty]
                    self._get_register_binding_dep_recursive(binding_ty, retrieved_composite_scope)
                else:
                    if is_singleton_composite(binding_found.scope):
                        # removing this for the potential of circular dependency.
                        retrieved_composite_scope.register_binding_idempotently(binding_ty, binding_found.provider)
                        self._context[binding_ty] = retrieved_composite_scope.get(binding_ty, binding_found.provider)
                        self.injector.binder.bindings[binding_ty] = binding_found
                    else:
                        self.get(binding_ty, binding_found.provider)

        else:
            LoggerFacade.info(f"Skipped {binding_ty} as dependency.")

    def __contains__(self, item: Type[T]):
        return item in self._context.keys()

    def __iter__(self):
        yield from self._context.items()

    def _is_valid_dep(self, ty):
        return 'Optional' not in str(ty)
