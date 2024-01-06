import asyncio
import threading
import typing
from typing import Optional

import injector as injector

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.init_env import EnvironmentProvider, retrieve_env_profile
from python_di.env.profile import Profile
from python_di.env.property_source import PropertySource
from python_di.inject.context_builder.profile_util import add_profile, create_add_profile_curry
from python_di.inject.prioritized_injectors import InjectorsPrioritized
from python_di.inject.profile_composite_injector.scopes.prototype_scope import PrototypeScopeDecorator
from python_util.concurrent.synchronized_lock_stripe import LockStripingLocks
from python_util.logger.logger import LoggerFacade

T = typing.TypeVar("T")

profile_locks = LockStripingLocks()

RegisterableModuleT = list[
    typing.Union[type[injector.Module], injector.Module, typing.Callable[[injector.Binder], None]]]

ConfigPropsT = typing.Union[dict[str, object], ConfigurationProperties, PropertySource]

injector_lock = threading.RLock()


class InjectionContextInjector:

    def __init__(self, dot_env_file_name: str = None):
        self.profile_props = None
        self.dot_env = dot_env_file_name
        self.injectors_dictionary: Optional[InjectorsPrioritized] = None
        self.environment = None
        self.lazy_set: asyncio.Event = asyncio.Event()
        self.did_initialize_env: asyncio.Event = asyncio.Event()
        self.did_initialize_init_factories: asyncio.Event = asyncio.Event()

    def initialize_env_profiles(self):
        from python_di.env.init_env import get_env_module
        from python_di.inject.prioritized_injectors import InjectorsPrioritized
        from python_di.env.env_properties import YamlPropertiesFilesBasedEnvironment
        from python_di.env.profile_config_props import ProfileProperties
        if not self.did_initialize_env.is_set():
            environment = get_env_module(self.dot_env)
            self.environment: YamlPropertiesFilesBasedEnvironment = environment
            profile_props = self.environment.register_config_property_type(
                ProfileProperties,
                ProfileProperties.fallback if hasattr(ProfileProperties, 'fallback') else None
            )
            self.injectors_dictionary = InjectorsPrioritized(profile_props)
            self.register_component_value([ProfileProperties], profile_props,
                                          profile=YamlPropertiesFilesBasedEnvironment.default_profile(),
                                          scope=injector.singleton)
            self.profile_props = profile_props
            self.environment.profiles = profile_props
            self.register_injector_from_module([EnvironmentProvider(self.environment)],
                                               retrieve_env_profile(),
                                               self.environment.self_profile.priority)
            self.did_initialize_env.set()

    @injector.synchronized(injector_lock)
    def initialize_injector_factories(self):
        self._do_init_providers_factories()

    def register_injector_from_module(self, mod: RegisterableModuleT,
                                      profile: typing.Union[Optional[str], Optional[object]] = None,
                                      priority: Optional[int] = None):
        from python_di.env.profile import Profile
        from python_di.env.env_properties import Environment
        if profile is None:
            self.injectors_dictionary.register_injector(mod, profile=Environment.default_profile())
        elif isinstance(profile, Profile):
            self.injectors_dictionary.register_injector(mod, profile=profile)
        else:
            assert isinstance(profile, str)
            self.injectors_dictionary.register_injector(mod, profile=self._retrieve_create_profile(profile, priority))

    def register_component(self, concrete: typing.Type[T], bindings: list[type],
                           scope, profile: Optional[str] = None):
        return self.injectors_dictionary.register_component(concrete, bindings, scope,
                                                            profile=self._retrieve_create_profile(profile))

    def register_component_multibinding(self,
                                        binding: typing.Callable,
                                        concrete_ty: typing.Type[T],
                                        scope, profile: Optional[str] = None):
        self.injectors_dictionary: InjectorsPrioritized = self.injectors_dictionary
        return self.injectors_dictionary.register_component_multibinding(concrete_ty, binding, scope,
                                                                         profile=self._retrieve_create_profile(profile))

    def register_component_binding(self,
                                   binding: typing.Union[injector.Provider[T], typing.Callable],
                                   concrete_ty: typing.Type[T],
                                   bindings: list[type], scope,
                                   profile: Optional[str] = None):
        self.injectors_dictionary: InjectorsPrioritized = self.injectors_dictionary
        return self.injectors_dictionary.register_component_binding(concrete_ty, bindings, binding, scope,
                                                                    profile=self._retrieve_create_profile(profile))

    def register_component_value(self, mod: list[type], bind_to: T, scope, priority: Optional[int] = None,
                                 profile: Optional[str] = None):
        self.injectors_dictionary.register_component_value(
            mod, bind_to, scope,
            profile=self._retrieve_create_profile(profile, priority) if not isinstance(profile, Profile)
            else profile
        )

    @injector.synchronized(injector_lock)
    def register_config_properties(self, type_to_register: typing.Type[T], fallback: Optional[str] = None,
                                   bindings: typing.List[typing.Type] = None):
        prop = self.environment.register_config_property_type(type_to_register, fallback)
        if prop is not None:
            if type_to_register not in self.injectors_dictionary:
                LoggerFacade.info(f"Registering config prop {type_to_register} as component value.")
                base_type = [type_to_register]
                if bindings is not None:
                    base_type.extend(bindings)
                self.register_component_value(base_type, prop, injector.singleton)
            LoggerFacade.info(f"Initialized {type_to_register} config property.")
        else:
            LoggerFacade.warn(f"Failed to initialize: {type_to_register}.")
        return prop

    def register_config_property_values(self, property_values: ConfigPropsT,
                                        profile: Optional[str] = None,
                                        priority: Optional[int] = None,
                                        prefix_name: Optional[str] = None):
        self.environment.register_config_property_values(property_values, profile, priority,
                                                         prefix_name)

    def get_interface(self, type_value: typing.Type[T], profile: Optional[str] = None,
                      scope: injector.ScopeDecorator = None, **kwargs) -> Optional[T]:
        created_profile = self._retrieve_create_profile(profile) if profile is not None else None
        found_obj = self._perform_injector(
            lambda i, exc, kwargs_found: self.get_binding(i, type_value, created_profile,
                                                          scope, **kwargs),
            profile, type_value, scope, False)
        if found_obj is not None:
            return found_obj
        else:
            LoggerFacade.warn(f"Could not find {type_value}.")

    def get_property_with_default(self, key, default, profile_name=None):
        if self.environment is not None:
            from python_di.env.env_properties import YamlPropertiesFilesBasedEnvironment
            self.environment: YamlPropertiesFilesBasedEnvironment = self.environment
            prop = self.environment.get_property_with_default(key, default, profile_name)
            if prop is not None:
                return prop
        return self._perform_injector(lambda i, t, kwargs_found: self._get_prop_currier(i, profile_name, key, default))

    def get_injector(
            self,
            ty: typing.Type[T],
            collapse: bool = True,
            profile_name: str = None
    ) -> typing.Generator[injector.Injector, None, None]:
        yield from self.injectors_dictionary.retrieve_injector(
            ty,
            collapse,
            profile=self._retrieve_create_profile(profile_name)
            if profile_name is not None else None
        )

    def _is_lazy_set(self):
        return self.lazy_set.is_set()

    def _retrieve_create_profile(self, profile, priority: Optional[int] = None):
        from python_di.env.profile import Profile
        from python_di.env.profile_config_props import ProfileProperties
        self.profile_props: Optional[ProfileProperties] = self.profile_props
        assert self.did_initialize_env.is_set()
        if profile is not None:
            assert isinstance(profile, str | Profile), "Was not profile."
        if isinstance(profile, str):
            self.profile_props.do_if_callable(lambda profile_props: profile not in profile_props,
                                              create_add_profile_curry(priority, profile))
            return self.profile_props[profile]
        elif profile is not None:
            assert isinstance(profile, Profile), f"{profile} was not Profile."
            self.profile_props.do_if_callable(lambda profile_props: profile not in profile_props,
                                              create_add_profile_curry(priority, profile, add_profile))
            return profile
        elif priority is not None:
            return self.profile_props.create_get_profile_with_priority(priority)
        else:
            from python_di.env.env_properties import Environment
            return Environment.default_profile()

    def _do_init_providers_factories(self):
        if not self.did_initialize_env.is_set():
            self.initialize_env_profiles()
        if not self.did_initialize_init_factories.is_set():
            lazy = False
        elif not self.lazy_set.is_set():
            lazy = True
        else:
            return
        for profile, factory in self.environment.load_factories(lazy):
            self.register_injector_from_module(factory, profile.profile_name, profile.priority)
        if lazy and not self._is_lazy_set():
            self.lazy_set.set()
        elif not lazy and not self.did_initialize_init_factories.is_set():
            self.did_initialize_init_factories.set()

    def _register_bean_mods(self, config, config_value, bindings, lazy_mods, profile_in):
        for bean_profile, mod in lazy_mods.items():
            if bean_profile is None:
                bean_profile = profile_in
            profile = self._retrieve_create_profile(bean_profile)
            self.injectors_dictionary.register_config_injector([mod], config, config_value,
                                                               bindings, profile=profile)

    def _sort_config_ky(self, priority: Optional[int], profile_name: Optional[str]):
        return priority if priority is not None \
            else self._retrieve_create_profile(profile_name) \
            if profile_name is not None else self.environment.default_profile().priority

    def _perform_injector(self, injector_cb: typing.Callable[[injector.Injector, list[Exception], dict], Optional[T]],
                          profile: Optional[str] = None, ty: typing.Type[T] = None, scope=None, collapse: bool = True,
                          **kwargs) -> Optional[T]:
        exceptions = []
        for injector_found in self.get_injector(ty, collapse, profile_name=profile):
            out_val = injector_cb(injector_found, exceptions, kwargs)
            if out_val is not None:
                return out_val

        # lazy can be unset by adding another configuration as the config files are interpreted and classes are loaded.
        if not self.did_initialize_env.is_set() or self._is_initialization_needed():
            if not self.did_initialize_env.is_set():
                self.initialize_env_profiles()
                return self._perform_injector(injector_cb, profile, ty, kwargs)
            elif self._is_initialization_needed():
                self.initialize_injector_factories()
                return self._perform_injector(injector_cb, profile, ty, kwargs)
        else:
            out = (f'Could not find value of type {ty if ty is not None else "**Not Provided**"} '
                   f'with the following errors.')
            for i, e in enumerate(exceptions):
                out += f"{i} exception: "
                out += str(e)
                out += "\n"
            LoggerFacade.debug(out)

    def _is_initialization_needed(self):
        return not self.lazy_set.is_set() or not self.did_initialize_init_factories.is_set()

    def _get_prop_currier(self, injector_value: injector.Injector, profile_name: str, key, default):
        return self.get_prop_from_injector(injector_value, profile_name, key, default)

    @classmethod
    def get_prop_from_injector(cls, injector_value: injector.Injector, profile, key, default):
        from python_di.env.base_env_properties import Environment
        env = injector_value.get(Environment)
        if env is not None:
            prop = env.get_property_with_default(key, default, profile)
            return prop
        else:
            LoggerFacade.error("Environment was not configured.")

    def contains_binding(self, type_value: typing.Type[T]) -> bool:
        return self.injectors_dictionary.contains_binding(type_value)

    @classmethod
    def get_binding(cls, injector_value: injector.Injector, type_value: typing.Type[T],
                    profile, scope_decorator: injector.ScopeDecorator = None,
                    **kwargs) -> Optional[T]:
        type_not_contained = type_value not in injector_value.binder._bindings.keys()
        if isinstance(scope_decorator, PrototypeScopeDecorator):
            if not hasattr(type_value, 'prototype_bean_factory_ty'):
                LoggerFacade.error(f"Attempted to retrieve {type_value} with prototype scope but the reference to the"
                                   f"bean's factory did not exist.")
            else:
                if type_value.prototype_bean_factory_ty in injector_value.binder._bindings.keys():
                    # prototype bean factory is singleton.
                    type_value = injector_value.get(type_value.prototype_bean_factory_ty, scope=injector.singleton)
                    return type_value.create(cls.retrieve_profile_name(profile), **kwargs)
        else:
            if isinstance(scope_decorator, injector.ScopeDecorator):
                scope_decorator = scope_decorator.scope
            if type_not_contained:
                LoggerFacade.debug(f"Could not find {type_value} with {injector_value.binder._bindings.__len__()} "
                                   f"number of bindings")
            else:
                binding, _ = injector_value.binder.get_binding(type_value)
                if scope_decorator is not None and binding.scope != scope_decorator:
                    LoggerFacade.error(f"Scope requested was {scope_decorator}, but scope contained in {profile} was "
                                       f"{binding.scope}.")
                elif scope_decorator is None:
                    scope_decorator = injector.singleton.scope
                return injector_value.get(type_value, scope_decorator)

    @classmethod
    def retrieve_profile_name(cls, profile):
        profile_name = None
        if profile is not None and hasattr(profile, 'profile_name'):
            profile_name = profile.profile_name
        elif profile is not None and isinstance(profile, str):
            profile_name = profile
        return profile_name.lower() if profile_name is not None else None
