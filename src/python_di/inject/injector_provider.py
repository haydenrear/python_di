import asyncio
import dataclasses
import os
import threading
import typing
from typing import Optional

import injector as injector
from injector import Binder

from python_util.concurrent.synchronized_lock_stripe import LockStripingLocks
from python_di.configs.base_config import DiConfiguration
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.init_env import EnvironmentProvider, retrieve_env_profile
from python_di.env.property_source import PropertySource
from python_di.inject.composite_injector import CompositeInjector, ProfileScope
from python_util.logger.logger import LoggerFacade
from python_util.reflection.reflection_utils import is_type_instance_of

T = typing.TypeVar("T")

injector_lock = threading.RLock()
profile_locks = LockStripingLocks()

RegisterableModuleT = list[
    typing.Union[type[injector.Module], injector.Module, typing.Callable[[injector.Binder], None]]]

ConfigPropsT = typing.Union[dict[str, object], ConfigurationProperties, PropertySource]

DEFAULT_PRIORITY = -100

ProfileT = typing.TypeVar("ProfileT")


@dataclasses.dataclass
class ConfigInitialization:
    config: typing.Type[DiConfiguration]
    underlying: typing.Type
    init_event: asyncio.Event
    lazy_event: asyncio.Event
    profile: Optional[str]
    priority: Optional[int]
    bindings: Optional[list[typing.Type]]


class InjectionContextInjector:

    def __init__(self, dot_env_file_name: str = None):
        self.profile_props = None
        self.dot_env = dot_env_file_name
        self.injectors_dictionary: Optional = None
        self.environment = None
        self.configurations: list[ConfigInitialization] = []
        self.lazy_set: asyncio.Event = asyncio.Event()
        self.did_initialize_env: asyncio.Event = asyncio.Event()

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
                os.path.join(os.path.dirname(__file__), 'fallback_profile_application.yml')
            )
            self.injectors_dictionary = InjectorsPrioritized(profile_props)
            self.profile_props = profile_props
            self.environment.profiles = profile_props
            self.register_injector_from_module([EnvironmentProvider(self.environment)],
                                               retrieve_env_profile(),
                                               self.environment.self_profile.priority)
            self.did_initialize_env.set()

    def initialize_injector_factories(self, lazy: bool = False,
                                      ty: Optional[typing.Type] = None,
                                      recursive: bool = False):
        """
        :param ty:
        :param recursive:
        :param lazy: If lazy is set to True, then this means that initialization has already happened and now
        will do lazy initializations.
        :return:
        """
        self._do_init_providers_factories(lazy)

        for config_init in self.configurations:
            _, config, event, lazy_event, _, _, _ = self.deconstruct_config_init(config_init)
            from python_di.inject.prioritized_injectors import InjectorsPrioritized
            self.injectors_dictionary: InjectorsPrioritized = self.injectors_dictionary

            if lazy_event.is_set():
                assert event.is_set()
            if event.is_set() and not lazy_event.is_set():
                self._do_lazy_init(config, config_init)
                # only initialize one module at a time and then check to see if contains ty.
                break
            elif not event.is_set():
                self._do_nonlazy_init(config_init, lazy)
                # only initialize one module at a time and then check to see if contains ty.
                break
            else:
                assert event.is_set() and lazy_event.is_set, \
                    f"Event was not set and lazy event was set for {config}."

        self._do_recurse_if_not_initialized(lazy, recursive, ty)

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

    def register_component_value(self, mod: list[type], bind_to: T, scope, priority: Optional[int] = None,
                                 profile: Optional[str] = None):
        self.injectors_dictionary.register_component_value(mod, bind_to, scope,
                                                           profile=self._retrieve_create_profile(profile, priority))

    def register_configuration(self, configuration: typing.Type[DiConfiguration], underlying: typing.Type,
                               profile: Optional[str] = None, priority: Optional[int] = None,
                               bindings: list[typing.Type] = None):
        self.configurations.append(ConfigInitialization(configuration, underlying, asyncio.Event(),
                                                        asyncio.Event(), profile, priority, bindings))
        from python_di.env.profile_config_props import ProfileProperties
        from python_di.inject.prioritized_injectors import InjectorsPrioritized
        self.injectors_dictionary: InjectorsPrioritized = self.injectors_dictionary
        self.profile_props: ProfileProperties = self.profile_props
        self.configurations = sorted(self.configurations, key=lambda c: self._sort_config_ky(c.priority, c.profile))

    def register_config_property_values(self, property_values: ConfigPropsT,
                                        profile: Optional[str] = None,
                                        priority: Optional[int] = None,
                                        prefix_name: Optional[str] = None):
        self.environment.register_config_property_values(property_values, profile, priority,
                                                         prefix_name)

    def get_interface(self, type_value: typing.Type[T], profile: Optional[str] = None,
                      scope: injector.ScopeDecorator = None) -> Optional[T]:
        created_profile = self._retrieve_create_profile(profile) if profile is not None else None
        self.initialize_injector_factories(self._is_lazy_set(), type_value)
        found_obj = self._perform_injector(lambda i, exc: self.get_binding(i, type_value, created_profile, scope),
                                           profile, type_value, scope)
        if found_obj is not None:
            return found_obj
        elif is_multibindable(type_value):
            from python_di.inject.prioritized_injectors import InjectorsPrioritized
            self.injectors_dictionary: InjectorsPrioritized = self.injectors_dictionary
            return self.injectors_dictionary.register_multibind(type_value, scope, created_profile)

    def get_property_with_default(self, key, default, profile_name=None):
        if self.environment is not None:
            from python_di.env.env_properties import YamlPropertiesFilesBasedEnvironment
            self.environment: YamlPropertiesFilesBasedEnvironment = self.environment
            prop = self.environment.get_property_with_default(key, default, profile_name)
            if prop is not None:
                return prop
        return self._perform_injector(lambda i, t: self._get_prop_currier(i, profile_name, key, default))

    def get_injector(self, ty: typing.Type[T], profile_name: str = None) -> typing.Generator[injector.Injector, None, None]:
        yield from self.injectors_dictionary.retrieve_injector(
            ty, profile=self._retrieve_create_profile(profile_name) if profile_name is not None else None)


    def _is_lazy_set(self):
        return self.lazy_set.is_set() and self._are_all_configs_lazy_set()

    def _are_all_configs_lazy_set(self):
        return (len(self.configurations) == 0
                or all([config_init.lazy_event.is_set() and config_init.init_event.is_set()
                    for config_init in self.configurations]))

    def _retrieve_create_profile(self, profile, priority: Optional[int] = None):
        from python_di.env.profile import Profile
        from python_di.env.profile_config_props import ProfileProperties
        self.profile_props: Optional[ProfileProperties] = self.profile_props
        assert self.did_initialize_env.is_set()
        if profile is not None:
            assert isinstance(profile, str | Profile)
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

    def _do_lazy_init(self, config, config_init):
        from python_di.configs.di_configuration import get_config_clzz
        profile_created = self._retrieve_create_profile(config_init.profile, config_init.priority)
        underlying_cnfg = get_config_clzz(config_init.config)
        config_value = self.injectors_dictionary.get_config_value(bindings=config_init.bindings,
                                                                  config_ty=underlying_cnfg)
        lazy_mods = config_value.lazy()
        self._register_bean_mods(config_init.config, config_value, config_init.bindings,
                                 lazy_mods, profile_created)
        config_init.lazy_event.set()
        LoggerFacade.info(f"Finished initializing config with type: {config}.")
        self.configurations.remove(config_init)

    def _do_nonlazy_init(self, config_init, lazy):
        from python_di.configs.di_configuration import get_config_clzz
        profile_created = self._retrieve_create_profile(config_init.profile, config_init.priority)
        underlying_cnfg = get_config_clzz(config_init.config)
        config_value = self.injectors_dictionary.create_config_value(bindings=config_init.bindings,
                                                                     config_ty=underlying_cnfg)
        initialize_mods = config_value.initialize()
        if lazy and not config_init.lazy_event.is_set():
            lazy_mods = config_value.lazy()
            self._register_bean_mods(underlying_cnfg, config_value, config_init.bindings,
                                     initialize_mods, profile_created)
            self._register_bean_mods(underlying_cnfg, config_value, config_init.bindings,
                                     lazy_mods, profile_created)
            config_init.lazy_event.set()
            LoggerFacade.info(f"Finished initializing config with type: {config_init.config}.")
            self.configurations.remove(config_init)
        else:
            if len(initialize_mods) != 0:
                self._register_bean_mods(underlying_cnfg, config_value, config_init.bindings,
                                         initialize_mods, profile_created)
            else:
                profile = self._retrieve_create_profile(config_init.profile)
                self.injectors_dictionary.register_config_injector([], underlying_cnfg, config_value,
                                                                   config_init.bindings, profile=profile)
        _set_class_configs(config_init.config, config_value, config_init.underlying)
        config_init.init_event.set()

    def _do_recurse_if_not_initialized(self, lazy, recursive, ty):
        if self._are_all_configs_lazy_set() and lazy:
            # When all configs are lazy set, lazy needs to be set, and then run again with lazy set to initialize
            # lazy factories.
            if not self.lazy_set.is_set():
                self.lazy_set.set()
                self.initialize_injector_factories(True, ty, True)
            if ty not in self.injectors_dictionary:
                LoggerFacade.info(
                    f"All configs are lazy set: {[str(i.lazy_event.is_set()) for i in self.configurations]} is lazy "
                    f"and init events {[str(i.init_event.is_set()) for i in self.configurations]}.")
        elif self.lazy_set.is_set():
            LoggerFacade.info("Unsetting lazy, as a configuration must have been added and it needs to be initialized.")
            self.lazy_set.clear()

        ty_not_contained_in_injector = ty not in self.injectors_dictionary
        does_require_initialization = (not recursive or not self._is_lazy_set()) and ty_not_contained_in_injector

        if does_require_initialization:
            self.initialize_injector_factories(self._are_all_configs_lazy_set(), ty, True)
        if ty not in self.injectors_dictionary and self._is_lazy_set() and lazy:
            LoggerFacade.error(f"Circular dependencies detected for {ty}.")

    def _do_init_providers_factories(self, lazy):
        if not self.did_initialize_env.is_set():
            self.initialize_env_profiles()
        for profile, factory in self.environment.load_factories(lazy):
            self.register_injector_from_module(factory, profile.profile_name, profile.priority)

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
                          profile: Optional[str] = None, ty: typing.Type[T] = None, scope=None,
                          **kwargs) -> Optional[T]:
        exceptions = []
        for injector_found in self.get_injector(ty, profile_name=profile):
            out_val = injector_cb(injector_found, exceptions, **kwargs)
            if out_val is not None:
                return out_val

        # lazy can be unset by adding another configuration as the config files are interpreted and classes are loaded.
        if not self.did_initialize_env.is_set():
            self.initialize_env_profiles()
            injector_performed = self._perform_injector(injector_cb, profile, ty, **kwargs)
            if injector_performed is not None:
                return injector_performed
            return self._perform_inject_iteration_recursive(injector_cb, profile, ty, **kwargs)
        if not self._is_lazy_set():
            return self._perform_inject_iteration_recursive(injector_cb, profile, ty, True, **kwargs)
        else:
            out = (f'Could not find value of type {ty if ty is not None else "**Not Provided**"} '
                   f'with the following errors.')
            for i, e in enumerate(exceptions):
                out += f"{i} exception: "
                out += str(e)
                out += "\n"
            LoggerFacade.debug(out)

    def _perform_inject_iteration_recursive(self,
                                            injector_cb: typing.Callable[
                                               [injector.Injector, list[Exception], dict], Optional[T]],
                                            profile: Optional[str] = None,
                                            ty: typing.Type[T] = None, lazy: bool = False, **kwargs) -> Optional[T]:
        injector_performed = None
        while not self._is_lazy_set() and injector_performed is None:
            self.initialize_injector_factories(lazy, ty)
            injector_performed = self._perform_injector(injector_cb, profile, ty, **kwargs)
        if injector_performed is not None:
            return injector_performed
        elif self._is_lazy_set():
            self.initialize_injector_factories(self._is_lazy_set(), ty)
            return self._perform_injector(injector_cb, profile, ty, **kwargs)

    def _get_prop_currier(self, injector_value: injector.Injector, profile_name: str, key, default):
        return self.get_prop_from_injector(injector_value, profile_name, key, default)

    @classmethod
    def deconstruct_config_init(cls, config_init):
        event: asyncio.Event = config_init.init_event
        lazy_event: asyncio.Event = config_init.lazy_event
        profile_name: Optional[str] = config_init.profile
        priority: Optional[int] = config_init.priority
        config = config_init.config
        underlying = config_init.underlying
        bindings = config_init.bindings
        return bindings, config, event, lazy_event, priority, profile_name, underlying


    @classmethod
    def get_prop_from_injector(cls, injector_value: injector.Injector, profile, key, default):
        from python_di.env.base_env_properties import Environment
        env = injector_value.get(Environment)
        if env is not None:
            prop = env.get_property_with_default(key, default, profile)
            return prop
        else:
            LoggerFacade.error("Environment was not configured.")

    @classmethod
    def get_binding(cls, injector_value: injector.Injector, type_value: typing.Type[T],
                    profile, scope_decorator: injector.ScopeDecorator = None) -> Optional[T]:
        if isinstance(scope_decorator, injector.ScopeDecorator):
            scope_decorator = scope_decorator.scope
        type_not_contained = type_value not in injector_value.binder._bindings.keys()
        if type_not_contained:
            LoggerFacade.info(f"Could not find {type_value} with {injector_value.binder._bindings.__len__()} "
                              f"number of bindings")
        else:
            binding, _ = injector_value.binder.get_binding(type_value)
            if isinstance(scope_decorator, injector.ScopeDecorator):
                scope_decorator = scope_decorator.scope
            if scope_decorator is not None and binding.scope != scope_decorator:
                LoggerFacade.error(f"Scope requested was {scope_decorator}, but scope contained in {profile} was "
                                   f"{binding.scope}.")
            return injector_value.get(type_value, binding.scope)



class InjectorInjectionModule(injector.Module):
    def configure(self, binder: Binder):
        binder.bind(InjectionContextInjector, to=InjectionContextInjector, scope=injector.singleton)


class InjectionContext:
    injection_context: InjectionContextInjector = (CompositeInjector([InjectorInjectionModule])
                                                   .get(InjectionContextInjector))

    @classmethod
    @injector.synchronized(injector_lock)
    def initialize_env(cls):
        if not cls.injection_context.did_initialize_env.is_set() is None:
            cls.injection_context.initialize_env_profiles()
            assert cls.injection_context.did_initialize_env.is_set()

    @classmethod
    @injector.synchronized(injector_lock)
    def register_injector_from_module(cls, mod: list[type[injector.Module]],
                                      profile: Optional[str] = None,
                                      priority: Optional[int] = None):
        LoggerFacade.info("Registering module injector.")
        cls.injection_context.register_injector_from_module(mod, profile, priority)

    @classmethod
    @injector.synchronized(injector_lock)
    def register_configuration(cls, configuration: typing.Type[DiConfiguration], underlying: typing.Type,
                               profile: Optional[str] = None, priority: Optional[str] = None,
                               bindings: list[typing.Type] = None):
        cls.initialize_env()
        cls.injection_context.register_configuration(configuration, underlying, profile, priority, bindings)

    @classmethod
    @injector.synchronized(injector_lock)
    def register_component(cls, concrete: typing.Type[T], bindings: list[type], scope, profile: Optional[str] = None):
        cls.initialize_env()
        return cls.injection_context.register_component(concrete, bindings, scope, profile)

    @classmethod
    @injector.synchronized(injector_lock)
    def register_component_value(cls, mod: list[type], bind_to: T, scope=None, priority: Optional[int] = None,
                                 profile: Optional[str] = None):
        cls.injection_context.register_component_value(mod, bind_to, scope, priority,  profile)

    @classmethod
    @injector.synchronized(injector_lock)
    def register_config_properties(cls, type_to_register: typing.Type[T], fallback: Optional[str] = None,
                                   bindings: typing.List[typing.Type] = None):
        cls.initialize_env()
        prop = cls.injection_context.environment.register_config_property_type(type_to_register, fallback)
        if prop is not None:
            if type_to_register not in cls.injection_context.injectors_dictionary:
                LoggerFacade.info(f"Registering config prop {type_to_register} as component value.")
                base_type = [type_to_register]
                if bindings is not None:
                    base_type.extend(bindings)
                cls.injection_context.register_component_value(base_type, prop, injector.singleton)
            LoggerFacade.info(f"Initialized {type_to_register} config property.")
        else:
            LoggerFacade.warn(f"Failed to initialize: {type_to_register}.")
        return prop

    @classmethod
    @injector.synchronized(injector_lock)
    def register_config_properties_value(cls, type_to_register: ConfigPropsT, profile: str, priority: int):
        cls.initialize_env()
        cls.injection_context.environment.register_config_property_values(type_to_register, profile, priority)
        return type_to_register

    @classmethod
    @injector.synchronized(injector_lock)
    def get_interface(cls, type_value: typing.Type[T], profile: str = None,
                      scope: injector.ScopeDecorator = None) -> Optional[T]:
        from python_di.configs.constants import DiUtilConstants
        if scope is None:
            scope = injector.singleton
        if hasattr(type_value, DiUtilConstants.prefix_name.name):
            cls.initialize_env()
            if cls.injection_context.environment.contains_property_prefix(type_value.prefix_name):
                prop = cls.injection_context.get_property_with_default(type_value.prefix_name, None, profile)
                if prop is None:
                    LoggerFacade.warn(f"Did not contain {type_value.prefix_name} for type {type_value} and profile "
                                      f"{profile}.")
                return prop
            else:
                if hasattr(type_value, 'fallback'):
                    LoggerFacade.warn(f"Did not contain {type_value.prefix_name} for type {type_value} and profile "
                                      f"{profile}, but contained fallback {type_value.fallback}. Attempting to load "
                                      f"from fallback.")
                    try:
                        fallback_value = type_value.fallback
                        cls.register_config_properties(type_value, fallback_value)
                        out = cls.get_interface(type_value, fallback_value)
                        return out
                    except Exception as e:
                        LoggerFacade.error(f"Failed to load from fallback with error {e}.")


        LoggerFacade.info(f"Retrieving {type_value}")
        out_value = cls.injection_context.get_interface(type_value, profile, scope)

        if out_value is not None:
            LoggerFacade.info(f"Found {type_value}.")
            return out_value
        elif hasattr(type_value, DiUtilConstants.proxied.name):
            return cls.injection_context.get_interface(type_value.proxied, profile, scope)

        return out_value

    @classmethod
    @injector.synchronized(injector_lock)
    def register_config_property_values(cls, property_values: ConfigPropsT,
                                        profile: Optional[str] = None,
                                        priority: Optional[int] = None,
                                        prefix_name: Optional[str] = None):
        cls.initialize_env()
        cls.injection_context.environment.register_config_property_values(property_values, profile, priority,
                                                                          prefix_name)

    @classmethod
    @injector.synchronized(injector_lock)
    def get_property_with_default(cls, key, default, profile_name=None):
        return cls.injection_context.get_property_with_default(key, default, profile_name)


def is_multibindable(type_to_check: typing.Type[T]):
    return (is_type_instance_of(type_to_check, dict)
            or is_type_instance_of(type_to_check, set)
            or is_type_instance_of(type_to_check, list))


def create_add_default_profile(profile_props, priority, profile):
    LoggerFacade.debug(f"Requested profile with name {profile}, "
                       f"but did not exist yet in prioritized injectors retrieve profile.")
    from python_di.env.profile import Profile
    assert isinstance(profile, str)
    if priority is None:
        priority = DEFAULT_PRIORITY
    new_profile = Profile.new_profile(profile, priority)
    profile_props[profile] = new_profile
    return new_profile


def add_profile(profile_props, priority, profile):
    from python_di.env.profile import Profile
    assert isinstance(profile, Profile)
    profile_props[profile.profile_name] = profile


def create_add_profile_curry(
        priority, profile,
        cb: typing.Callable[[ProfileT, int, ProfileT], object] = create_add_default_profile):
    LoggerFacade.debug(f"Requested profile with name {profile}, "
                       f"but did not exist yet in prioritized injectors retrieve profile.")
    return lambda profile_props: cb(profile_props, priority, profile)


def _set_class_configs(config, config_value, underlying):
    from python_di.configs.constants import DiUtilConstants
    config.proxied = underlying
    if hasattr(underlying, DiUtilConstants.class_configs.name) and config_value not in underlying.class_configs:
        underlying.class_configs.append(config_value)
    elif config_value:
        underlying.class_configs = [config_value]
