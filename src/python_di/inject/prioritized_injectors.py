import abc
import collections
import threading
import typing
from typing import Optional

import injector

from python_di.env.base_env_properties import Environment
from python_di.env.profile import Profile
from python_di.inject.composite_injector import CompositeInjector, CompositeScope, ProfileScope, profile_scope, \
    composite_scope
from python_di.inject.inject_utils import is_scope_singleton_scope
from python_di.inject.injection_field import InjectionObservationField
from python_di.inject.injector_provider import RegisterableModuleT, is_multibindable
from python_di.inject.reflectable_ctx import bind_multi_bind
from python_util.concurrent.synchronized_lock_stripe import synchronized_lock_striping, LockStripingLocks
from python_util.logger.logger import LoggerFacade

T = typing.TypeVar("T")
MultiBindTypeT = typing.TypeVar("MultiBindTypeT")


class InjectorsInjecting(abc.ABC):
    def retrieve_injector(self, ty: typing.Type[T]):
        pass

    def register_component_value(self, mod: list[type], bind_to: T, profile: Optional[str] = None):
        pass


class GraphInformedDependencyResolvingInjectors(InjectorsInjecting):
    pass


config_ty_locks = LockStripingLocks()
profile_locks = LockStripingLocks()
synchronized_lock = threading.RLock()


def log_binder_info(inj):
    if isinstance(inj, injector.Injector):
        LoggerFacade.debug(f"Yielding next injector with {len(inj.binder._bindings)} num "
                           f"bindings")


class SingletonBindingExistedException(BaseException):
    pass


class ConfigNotExistedException(BaseException):
    pass


class ProfileBindingNotExistedException(BaseException):
    pass


class InjectorsPrioritized:
    """
    Uses a shared composite scope with all singletons between all profiles so that any profile can access any
    singleton, but the bindings in the profiles are distinguished from each other. Therefore, if a profile is
    specified, then any bindings within the type to be retrieved that are profile scope will be included. If it
    is a singleton, the binding with the highest precedence is used that exists at the time of the creation of,
    the value. The priority is used to determine the precedence.
    """

    def __init__(self, profile_props):
        """
        :param profile_props:
        """
        from python_di.env.profile_config_props import ProfileProperties
        default_profile = Environment.default_profile()
        self.profile_props = profile_props
        self.profile_scopes = {}
        self.injectors: typing.OrderedDict[Profile, InjectionObservationField] = collections.OrderedDict({})
        composite_injector = CompositeInjector([], profile=default_profile)
        self.profile_scopes[default_profile.profile_name] = composite_injector.get(ProfileScope)
        self.composite_scope: CompositeScope = CompositeScope(composite_injector)
        composite_injector.composite_created = self.composite_scope
        self.injectors[default_profile] = InjectionObservationField(
            [composite_injector],
            profile_scope=self.profile_scopes[default_profile.profile_name],
            composite_scope=self.composite_scope
        )
        bind_composite_scope(composite_injector, self.composite_scope)
        self.config_idx: dict[typing.Type, Profile] = {}
        self.profiles: Optional[ProfileProperties] = None
        self.multibind_registrar: dict[typing.Type, typing.List[typing.Type]] = {}

    @synchronized_lock_striping(config_ty_locks, lock_arg_arg_name='config_ty')
    def create_config_value(self, bindings=None, config_ty=None):
        for p, i in self.injectors.items():
            i: InjectionObservationField = i
            existed_config = i.retrieve_injector()
            if existed_config is not None and config_ty in existed_config.binder._bindings.keys():
                found = existed_config.get(config_ty)
                if found is not None:
                    create_bindings_inner(bindings, lambda: found, existed_config)
                    return found

        LoggerFacade.info(f"Created new config ty for {config_ty}.")
        created = create_config_ty(config_ty)
        return created

    @synchronized_lock_striping(config_ty_locks, lock_arg_arg_name='config_ty')
    def get_config_value(self, bindings=None, config_ty=None):
        for p, i in self.injectors.items():
            i: InjectionObservationField = i
            existed_config = i.retrieve_injector()
            if existed_config is not None and config_ty in existed_config.binder._bindings.keys():
                found = existed_config.get(config_ty)
                LoggerFacade.info(f"Found {found} in config value.")
                create_bindings_inner(bindings, found, existed_config)
                return found
        raise ConfigNotExistedException(f"Config {config_ty} did not exist.")

    @synchronized_lock_striping(profile_locks, lock_arg_arg_name='profile')
    def register_config_injector(self,
                                 inject_value: RegisterableModuleT,
                                 config_ty,
                                 config_value,
                                 bindings,
                                 profile: Profile):
        """
        This takes in a config injector and attempts to build it using currently available dependencies. It walks through
        the current modules backwards and adds them so that those with highest precedence will be used. This so that
        if the Configuration contains other dependencies provided in other Configurations, they will be able to be
        resolved.
        :param config_value:
        :param inject_value:
        :param config_ty:
        :param profile:
        :return:
        """
        if profile not in self.injectors.keys():
            new_injector = create_bind_new_config_injector(bindings, config_ty, config_value, inject_value,
                                                           self.composite_scope, profile, None)
            bind_composite_scope(new_injector, self.composite_scope)
            self.profile_scopes[profile.profile_name] = new_injector.get(ProfileScope, ProfileScope)
            self.injectors[profile] = InjectionObservationField(
                config_injectors={config_ty: [new_injector]},
                profile_scope=self.profile_scopes[profile.profile_name],
                composite_scope=self.composite_scope
            )
        else:
            new_injector = create_bind_new_config_injector(bindings, config_ty, config_value, inject_value,
                                                           self.composite_scope, profile,
                                                           self.profile_scopes[profile.profile_name])
            bind_composite_scope(new_injector, self.composite_scope)
            self.injectors[profile].register_config_injector(new_injector, config_ty)

    @synchronized_lock_striping(profile_locks, lock_arg_arg_name='profile')
    def register_injector(self, inject_value: RegisterableModuleT, profile: Profile):
        """

        :param inject_value:
        :param profile:
        :return:
        """
        if profile.profile_name not in self.profile_props:
            self.profile_props[profile.profile_name] = profile
        if profile not in self.injectors.keys():
            created_injector = CompositeInjector(inject_value, profile=profile, scope=self.composite_scope)
            LoggerFacade.debug(f"Adding new profile {profile} to {[i for i in self.injectors.keys()]}.")
            self.profile_scopes[profile.profile_name] = created_injector.get(ProfileScope, ProfileScope)
            self.injectors[profile] = InjectionObservationField(injectors=[created_injector],
                                                                profile_scope=self.profile_scopes[profile.profile_name],
                                                                composite_scope=self.composite_scope)
        else:
            LoggerFacade.debug(f"Appending new injector {profile}.")
            created_injector = CompositeInjector(inject_value, profile=self.profile_scopes[profile.profile_name],
                                                 scope=self.composite_scope)

            self.injectors[profile].register_injector(created_injector)
        LoggerFacade.debug(f"After adding new profile {profile} to {[i for i in self.injectors.keys()]}.")

    @injector.synchronized(synchronized_lock)
    def yield_all_inj(self, ty: typing.Type, exclusions: set[Profile] = None):
        for p, j in sorted(self.injectors.items(), key=lambda k_v: k_v[0].priority, reverse=True):
            if exclusions is not None and p in exclusions:
                continue
            j: InjectionObservationField = j
            inj = j.collapse_injectors()
            log_binder_info(inj)
            self._do_bind_multibind_composite(inj, p, ty)
            yield inj

    @synchronized_lock_striping(profile_locks, lock_arg_arg_name='profile')
    def register_component_value(self, mod: list[type], bind_to: T, scope, profile: Profile):
        self._assert_valid_binding(bind_to, mod, profile, scope)
        LoggerFacade.info(f"Registering component value for profile {profile}.")
        injector_found: injector.Injector = next(self.retrieve_injector(type(bind_to), profile=profile))
        if isinstance(scope, injector.ScopeDecorator):
            scope = scope.scope
        mod_type = type(bind_to)
        if scope is None or is_scope_singleton_scope(scope):
            if self._do_check_if_bound(mod[0], bind_to):
                raise SingletonBindingExistedException(f"Failed to create binding for {mod_type}.")
        provider = injector.InstanceProvider(bind_to)
        for m in mod:
            if not binder_contains_item(injector_found, m):
                injector_found.binder.bind(m, provider, scope=scope)
        if mod_type not in mod:
            injector_found.binder.bind(mod_type, provider, scope=scope)

        self.do_init_multibind(mod, type(bind_to), injector_found)

    @synchronized_lock_striping(profile_locks, lock_arg_arg_name='profile')
    def register_component(self, concrete: typing.Type[T], bindings: list[typing.Type],
                           scope, profile: Profile = None):
        assert isinstance(profile, Profile)
        if scope is None or is_scope_singleton_scope(scope):
            if self._do_check_if_bound(concrete):
                raise SingletonBindingExistedException(f"Failed to create binding for {concrete}.")

        self._do_component_binding(bindings, concrete, profile, scope)

    @synchronized_lock_striping(profile_locks, lock_arg_arg_name='profile')
    def register_multibind(self, to_get_multibind: typing.Type[T], scope,
                           profile: Profile) -> typing.Optional[T]:
        if to_get_multibind in self.multibind_registrar.keys():
            injector_found: injector.Injector = next(self.retrieve_injector(to_get_multibind, profile=profile))
            multibind_ = self.multibind_registrar[to_get_multibind]
            do_injector_bind(to_get_multibind, injector_found, multibind_)
            return injector_found.get(to_get_multibind)
        else:
            self.multibind_registrar[to_get_multibind] = []
            return []

    def retrieve_injector(self, ty: typing.Type[T],
                          profile: Profile) -> typing.Generator[injector.Injector, None, None]:

        self._assert_injectors(profile, ty)
        if profile is not None and profile not in self.injectors.keys():
            composite_injector = create_bind_new_injector([], self.composite_scope, profile)
            self.profile_scopes[profile.profile_name] = composite_injector.get(ProfileScope, ProfileScope)
            self.injectors[profile] = InjectionObservationField(injectors=[composite_injector],
                                                                profile_scope=self.profile_scopes[profile.profile_name],
                                                                composite_scope=self.composite_scope)
            self._do_bind_multibind_composite(composite_injector, profile, ty)
            yield composite_injector
        if profile is None or profile not in self.injectors.keys() or len(self.injectors[profile]) == 0:
            if profile in self.injectors.keys():
                LoggerFacade.warn("Logger was empty but contained entry.")
            yield from self.yield_all_inj(ty)
        else:
            yield from self._yield_single_profile(ty, profile)
            yield from self.yield_all_inj(ty, {profile})

    def _do_bind_multibind_composite(self, composite_injector, profile, ty):
        multibind_ty = typing.List[ty]
        if multibind_ty in self.multibind_registrar.keys() and ty not in composite_injector:
            if len(self.multibind_registrar[multibind_ty]) != 0:
                scope_value = self.composite_scope if profile is None else self.profile_scopes[profile.profile_name]
                composite_injector.multibind(
                    multibind_ty,
                    lambda: self.get_multibindable(profile_scope if scope_value is not None
                                                   else composite_scope,
                                                   composite_injector, ty),
                    scope=scope_value
                )

    def get_multibindable(self, scope_value, composite_injector, ty):
        out = []
        for m in self.multibind_registrar[typing.List[ty]]:
            out.append(composite_injector.get(m, scope_value))
        return out

    def _yield_single_profile(self, ty: typing.Type, profile):
        next_profile = self.injectors[profile]
        composite_injector = next_profile.collapse_injectors()
        self._do_bind_multibind_composite(composite_injector, profile, ty)
        yield composite_injector

    def _do_check_if_bound(self, concrete, concrete_value=None):
        """
        In the event that there is a profile scope binding currently existing, then that will only exist in the
        profile scope even if it is retrieved from singleton scope. If a singleton scope is then added, it will
        override for singleton scope.
        :param concrete:
        :param concrete_value:
        :return:
        """

        num_profile_binding_used = sum([1 for profile_scope in self.profile_scopes.values()
                                        if concrete in profile_scope])
        profile_binding_used = num_profile_binding_used != 0
        composite_binding_used = concrete in self.composite_scope
        concrete_exists = concrete in self

        if profile_binding_used or composite_binding_used or (concrete_exists and concrete_value):
            self._log_failed_binding_already_existed(concrete, concrete,
                                                     concrete_value,
                                                     num_profile_binding_used,
                                                     profile_binding_used)
            return True
        elif concrete_exists and not concrete_value:
            LoggerFacade.warn(f"Attempted to register {concrete} twice, but only interface, not a second singleton "
                              f"value.")

    def _do_component_binding(self, bindings, concrete, profile, scope, concrete_value=None):
        injector_found: injector.Injector = next(self.retrieve_injector(concrete, profile=profile))
        if not binder_contains_item(injector_found, concrete):
            injector_found.binder.bind(concrete,
                                       concrete if concrete_value is None else concrete,
                                       scope=scope)
        self.do_init_multibind(bindings, concrete, injector_found)

    def do_init_multibind(self, bindings, concrete, injector_found):
        for b in bindings:
            if not binder_contains_item(injector_found, b):
                do_injector_bind(b, injector_found, concrete)
            self._bind_multibind_inner(b, concrete)
        self._bind_multibind_inner(concrete, concrete)

    def _bind_multibind_inner(self, b, concrete):
        if typing.List[b] in self.multibind_registrar.keys():
            if concrete not in self.multibind_registrar[typing.List[b]]:
                self.multibind_registrar[typing.List[b]].append(concrete)
        else:
            self.multibind_registrar[typing.List[b]] = [concrete]

    def _retrieve_injectors_having(self, ty: typing.Type[T]) -> dict[Profile, CompositeInjector]:
        return dict(filter(lambda k_v: ty in k_v[1], self.injectors.items()))

    def _injector_for(self, ty: typing.Type[T]) -> (Profile, CompositeInjector):
        for p, j in self.injectors.items():
            if ty in j:
                return p, j
        return None, None

    def __contains__(self, item: typing.Type[T]):
        for inject_value in self.injectors.values():
            for found_value in inject_value.injectors:
                if binder_contains_item(found_value, item):
                    return True
                else:
                    if binder_contains_item(found_value, item):
                        return True
            for found_value in [j for i in inject_value.config_injectors.values()
                                for j in i]:
                if binder_contains_item(found_value, item):
                    return True
                else:
                    if binder_contains_item(found_value, item):
                        return True

    @staticmethod
    def _log_failed_binding_already_existed(concrete, existed, value, num_profile, profile_being_used):
        LoggerFacade.debug(f"Received request to bind {concrete} in singelton scope when binding already "
                           f"existed. Request was to bind interface {concrete} again and new value was not "
                           f"created.")
        if existed and value:
            LoggerFacade.error(f"Received request to bind {concrete}. When requesting for the rebind a value was "
                               f"provided to rebind: {value}, but the type {concrete} had already been built and "
                               f"so this had to be ignored.")
        if num_profile != 0:
            LoggerFacade.error(f"Error when attempting to bind singleton for {concrete}. There already existed "
                               f"{num_profile} ProfileScope bindings for this type. There cannot be a singleton scope "
                               f"binding for a type with ProfileScope bindings.")
        if profile_being_used:
            LoggerFacade.error(f"Error when attempting to register singleton for {concrete}. There already existed "
                               f"a singleton scope binding for {concrete} that was already instantiated.")

    def _assert_injectors(self, profile, ty):
        assert isinstance(profile, Profile | None)
        if len(self.injectors) == 0:
            raise ValueError("Requested injector before any injectors were set.")
        if len(self.injectors) == 0 and len(self.injectors[profile]) != 0:
            LoggerFacade.error(f"Attempted to access injector for {ty} before config was collapsed.")

    def _assert_valid_binding(self, bind_to, mod, profile, scope):
        assert isinstance(profile, Profile)
        assert hasattr(bind_to, '__class__'), f"Attempted to bind {bind_to} but does not have ty to bind to."
        binding_ty = bind_to.__class__
        if binding_ty in self and is_scope_singleton_scope(scope):
            profile_i, i = self._injector_for(binding_ty)
            if profile != profile_i:
                LoggerFacade.info(f"Received second singleton scope binding for {binding_ty} for other profile "
                                  f"{profile} from {profile_i}. Adding the binding, but the profile with higher "
                                  f"precedence will be the only available binding in the context, as it is a "
                                  f"singleton.")
                return binding_ty
            else:
                raise ValueError(f"Received request to bind value {bind_to} to {binding_ty} and "
                                 f"{mod} in singleton scope, but binding already existed. Overwriting binding with "
                                 f"component value.")
        return binding_ty


def binder_contains_item(inject_value, item):
    return item in inject_value.binder._bindings.keys()


def get_binding_from_injector(injector_value: injector.Injector, ty):
    assert ty in injector_value.binder._bindings.keys()
    retrieve = injector_value.get(ty)
    return retrieve


def _injection_provider(ty: typing.Type[T], injector_value: injector.Injector) -> injector.Provider[T]:
    return injector.CallableProvider(lambda: get_binding_from_injector(injector_value, ty))


def create_config_ty(config):
    config_value = config()
    return config_value


def create_bind_new_injector(inject_value, composite_scope, profile):
    composite_injector = CompositeInjector(inject_value, profile=profile, scope=composite_scope)
    composite_injector.bind(injector.SingletonScope, composite_scope, scope=injector.singleton)
    composite_injector.bind(CompositeScope, composite_scope, scope=injector.singleton)
    return composite_injector


def create_bind_new_config_injector(bindings, config_ty, config_value, inject_value, composite_scope, profile,
                                    profile_scope):
    composite_injector = CompositeInjector(inject_value,
                                           profile=profile_scope if profile_scope is not None else profile,
                                           scope=composite_scope)
    composite_injector.bind(config_ty, injector.InstanceProvider(config_value), scope=injector.singleton)
    bind_composite_scope(composite_injector, composite_scope)
    if bindings is not None:
        for b in bindings:
            composite_injector.bind(b, injector.InstanceProvider(config_value), scope=injector.singleton)

    return composite_injector


def bind_composite_scope(composite_injector, composite_scope):
    composite_injector.bind(injector.SingletonScope, composite_scope, scope=injector.singleton)
    composite_injector.bind(CompositeScope, composite_scope, scope=injector.singleton)


def create_bindings_inner(bindings, config_value, existed_config):
    if bindings is not None:
        for b in bindings:
            if b not in existed_config.binder._bindings.keys():
                do_injector_bind(b, existed_config, injector.InstanceProvider(config_value))


def do_injector_multi(injector_found, multibind_, to_get_multibind, scope):
    if isinstance(injector_found, CompositeInjector):
        injector_found.multibind(to_get_multibind, multibind_, scope=injector.singleton if scope is None else scope)
    else:
        injector_found.binder.multibind(to_get_multibind, multibind_,
                                        scope=injector.singleton if scope is None else scope)


def do_bind(binder: injector.Binder, interface, provider, scope):
    try:
        is_mu = is_multibindable(interface)
    except:
        is_mu = True
    if is_mu:
        binder.multibind(interface, provider, scope)
    else:
        binder.bind(interface, provider, scope)


def do_injector_bind(interface, injector_found, provider, scope=None):
    try:
        is_mu = is_multibindable(interface)
    except:
        is_mu = True
    if is_mu:
        do_injector_multi(injector_found, provider, interface, scope)
    else:
        if isinstance(injector_found, CompositeInjector):
            injector_found.bind(interface, provider, scope=injector.singleton if scope is None else scope)
        else:
            injector_found.binder.bind(interface, provider, scope=injector.singleton if scope is None else scope)
