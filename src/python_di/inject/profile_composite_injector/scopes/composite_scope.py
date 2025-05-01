import inspect
import sys
import threading
import typing
from typing import Type

import injector
from injector import Provider, synchronized, T, InstanceProvider, UnsatisfiedRequirement

from python_di.env.profile import Profile
from python_di.inject.profile_composite_injector.multibind_util import is_multibindable
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope
from python_util.logger.logger import LoggerFacade

lock = threading.RLock()


class CompositeScope(injector.SingletonScope):
    """
    Manages creation and context of objects.
    """
    _context: dict[type, Provider] = {}

    def __init__(self, injector_added: injector.Injector):
        super().__init__(injector_added)

    @synchronized(lock)
    def get(self, key: Type[T], provider: Provider[T] = None, profile: Profile = None) -> Provider[T]:
        if key in self._context.keys():
            return self._context[key]
        else:
            # because by this time all values are added to the context, including all ProfileScope added to
            # the injector, can try to get the provider, and if it fails iterate through the profiles in priority
            # order and add to the CompositeScope _context and/or the top-level injector.
            try:
                provided = injector.InstanceProvider(provider.get(self.injector))
            except (TypeError, UnsatisfiedRequirement) as e:
                try:
                    provided = self.do_get_provided(e, key, provider)
                except Exception as next_exc:
                    LoggerFacade.error(f'Found exc: {next_exc}')
                    raise next_exc
            except Exception as e:
                LoggerFacade.error(f"{e}")
                raise e

            self.register_binding_idempotently(key, provided)
            self._context[key] = provided
            return provided

    def do_get_provided(self, e, key, provider):
        from python_di.inject.profile_composite_injector.composite_injector import composite_scope
        LoggerFacade.debug(f"Found error: {e}")
        all_profile_scopes: typing.List[ProfileScope] \
            = self.injector.get(typing.List[ProfileScope], scope=composite_scope)
        if isinstance(provider, injector.ClassProvider):
            cls_found = provider._cls
            self._try_fix_dep_bindings(all_profile_scopes, cls_found.__init__)
        elif isinstance(provider, injector.CallableProvider):
            callable_found = provider._callable
            self._try_fix_dep_bindings(all_profile_scopes, callable_found)
        else:
            LoggerFacade.error(f"Error getting {key}. Could not retrieve from profile because was provider "
                               f"of type {provider.__class__.__name__}")
            raise e
        provided = injector.InstanceProvider(provider.get(self.injector))
        return provided

    def _try_fix_dep_bindings(self, all_profile_scopes, fn_bound):
        """
        Sometimes a dependency will be bound in a profile scope, in which case the value needs to be added to this
        context as well.
        :param all_profile_scopes:
        :param fn_bound:
        :return:
        """
        bindings_created = injector.get_bindings(fn_bound)
        for binding_key, binding_ty in bindings_created.items():
            for p in self._iter_profile_scope(all_profile_scopes):
                if binding_ty in self.injector.binder._bindings.keys():
                    if binding_ty in self._context.keys():
                        continue
                    else:
                        try:
                            # the problem here is when ClassProviders are added with no dependencies and no scope.
                            binding: injector.Binding = self.injector.binder.get_binding(binding_ty)[0]
                            provider = binding.provider
                            scope = binding.scope
                            if scope != injector.NoScope and scope != injector.noscope:
                                self._context[binding_ty] = self.get(binding_ty, provider)
                                break
                            else:
                                LoggerFacade.info(f"Deleted no scope binding for {binding_ty} found in composite "
                                                  f"scope.")
                                del self.injector.binder._bindings[binding_ty]
                        except:
                            del self.injector.binder._bindings[binding_ty]
                if binding_ty in p.injector.binder._bindings.keys():
                    try:
                        binding_found = p.injector.binder.get_binding(binding_ty)[0]
                        provider: injector.Provider = binding_found.provider
                        if binding_found.scope != injector.NoScope and binding_found.scope != injector.noscope:
                            created = p.get(binding_ty, provider)
                            LoggerFacade.debug(f"Set provider {provider} for {binding_ty} in profile {p}")
                            self.register_binding_idempotently(binding_ty, created)
                            self._context[binding_ty] = created
                            break
                        else:
                            LoggerFacade.info(f"Deleted no scope binding for {binding_ty} found in composite "
                                              f"scope.")
                            del p.injector.binder._bindings[binding_ty]
                    except:
                        continue

    def _iter_profile_scope(self, all_profile_scopes):
        return sorted(all_profile_scopes,
                      key=lambda next_profile_scope: next_profile_scope.profile,
                      reverse=True)

    def _get_fn(self, binding_ty, injector_fn):
        ty__provider = injector_fn.binder.get_binding(binding_ty)[0].provider
        if isinstance(ty__provider, injector.CallableProvider):
            return ty__provider._callable, ty__provider
        elif isinstance(ty__provider, injector.ClassProvider):
            return ty__provider._cls.__init__, ty__provider

    def register_binding_idempotently(self, key, provider):
        from python_di.inject.profile_composite_injector.composite_injector import composite_scope
        if key in self._context.keys():
            assert key in self.injector.binder._bindings.keys(),\
                f"{key} was in context but was not registered in bindings."
            ctx = self._context[key]
            return ctx
        if key not in self.injector.binder._bindings.keys():
            if is_multibindable(key):
                self.injector.binder.multibind(key, provider, composite_scope)
            else:
                self.injector.binder.bind(key, provider, composite_scope)

    def register_binding(self, key: Type[T], value: T):
        self._context[key] = InstanceProvider(value)

    def delete_binding(self, key: Type[T]):
        if key in self._context.keys():
            del self._context[key]

    def __contains__(self, item: Type[T]):
        return item in self._context.keys()

    def __iter__(self):
        yield from self._context.items()
