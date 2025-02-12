import dataclasses
import os
import threading
import typing
import uuid
from typing import Optional

import injector

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from python_util.logger.logger import LoggerFacade

injector_lock = threading.RLock()


@configuration_properties(
    prefix_name='profiles',
    fallback=os.path.join(os.path.dirname(__file__), 'fallback_profile_application.yml')
)
class ProfileProperties(ConfigurationProperties):

    from python_di.env.profile import Profile
    active_profiles: typing.Dict[str, Profile]
    default_profile: Profile

    @injector.synchronized(injector_lock)
    def __setitem__(self, key, value):
        self.active_profiles[key] = value

    @injector.synchronized(injector_lock)
    def __getitem__(self, key):
        if key not in self.active_profiles.keys():
            return None
        return self.active_profiles[key]

    @injector.synchronized(injector_lock)
    def __contains__(self, item):
        return item in self.active_profiles.keys()

    @injector.synchronized(injector_lock)
    def do_if_callable(self, predicate, callable_value):
        if predicate(self):
            callable_value(self)

    @injector.synchronized(injector_lock)
    def retrieve_profile_with_priority(self, priority: int):
        for p, v in self.active_profiles.items():
            if v.priority == priority:
                return v

    @injector.synchronized(injector_lock)
    def create_get_profile_with_priority(self, priority: int):
        from python_di.env.profile import Profile
        profile = self.retrieve_profile_with_priority(priority)
        if profile is not None:
            return profile
        else:
            profile = Profile.new_profile(str(uuid.uuid4()), priority)
            LoggerFacade.info(f"Created new profile: {profile}.")
            self[profile.profile_name] = profile
            return profile

    @injector.synchronized(injector_lock)
    def create_get_profile(self, profile_name: str, priority_set: typing.Optional[int] = None):
        from python_di.env.profile import Profile
        assert profile_name is not None
        from python_di.inject.context_builder.profile_util import DEFAULT_PRIORITY
        priority = DEFAULT_PRIORITY
        if profile_name in self.active_profiles:
            return self.active_profiles[profile_name]
        else:
            if priority_set is not None:
                priority = priority_set
            self.active_profiles[profile_name] = Profile.new_profile(profile_name, priority)
            return self.active_profiles[profile_name]

    def profiles_sorted_by_priority(self) -> list[...]:
        return [
            v for k, v in sorted(self.active_profiles.items(), key=lambda k_v: k_v[1], reverse=True)
        ]

    @injector.synchronized(injector_lock)
    def create_get_profile_name_priority(self, priority: Optional[int] = None,
                                         profile_name: Optional[str] = None):
        from python_di.env.profile import Profile
        from python_di.env.env_properties import Environment
        if profile_name is None and priority is not None:
            return self.create_get_profile_with_priority(priority)
        if profile_name is not None and priority is None:
            return self.create_get_profile(profile_name)
        elif profile_name is None and priority is None:
            return Environment.default_profile()
        else:
            assert profile_name is not None and priority is not None and isinstance(profile_name, str)
            if profile_name in self.active_profiles.keys():
                if self.active_profiles[profile_name].priority == priority:
                    return self.active_profiles[profile_name]
                else:
                    found_profile = self.create_get_profile_with_priority(priority)
                    LoggerFacade.warn(f"Profile requested with priority {priority} with profile name {profile_name} "
                                      f"where profile name already existed. {profile_name} already existed, and "
                                      f"so {found_profile.profile_name} was used with priority "
                                      f"{found_profile.priority}.")
                    return found_profile
            else:
                profile = Profile.new_profile(profile_name, priority)
                LoggerFacade.info(f"Created new profile {profile.profile_name} with priority {priority}")
                self.active_profiles[profile.profile_name]  = profile
                return profile

def get_profile_module() -> ProfileProperties:
    from python_di.inject.context_builder.injection_context import InjectionContext
    profile_props: ProfileProperties = InjectionContext.get_interface(ProfileProperties)
    profile_props.active_profiles = sorted(profile_props.active_profiles)
    return profile_props
