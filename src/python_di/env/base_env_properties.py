import logging
from abc import ABC, abstractmethod
from typing import Optional

from python_di.env.env_factories import Factories
from python_di.env.profile import Profile
from python_di.env.profile_config_props import ProfileProperties
from python_di.env.property_source import PropertySource
PropertyPrefix = str
DEFAULT_PROFILE: str = 'main_profile'
DEFAULT_PRIORITY = 1000000


class Environment(ABC):

    _default_profile = Profile.new_profile(DEFAULT_PROFILE, DEFAULT_PRIORITY)

    @abstractmethod
    def get_property(self, key: str, profile: Optional[str] = None) -> object:
        pass

    @abstractmethod
    def get_property_with_default(self, key: str, default: str, profile: Optional[str] = None) -> object:
        pass

    def get_property_as_int_with_default(self, key: str, default: int, profile: Optional[str] = None) -> int:
        out = self.get_property_with_default(key, str(default), profile)
        try:
            if not isinstance(out, str):
                logging.error(f"Returned property {key} value {out} was not str.")
            return int(out)
        except:
            logging.error(f"Could not get property {key} as default. Returning {default}")
            return default

    @abstractmethod
    def set_property(self, key: str, value: object, profile: Optional[str] = None):
        pass

    @property
    @abstractmethod
    def self_profile(self) -> Profile:
        pass

    @property
    @abstractmethod
    def factories(self) -> Factories:
        pass

    @property
    @abstractmethod
    def profiles(self) -> ProfileProperties:
        pass

    @property
    @abstractmethod
    def config_properties(self) -> dict[Profile, PropertySource]:
        pass

    @config_properties.setter
    @abstractmethod
    def config_properties(self, config_properties: dict[Profile, PropertySource]):
        pass

    @property
    @abstractmethod
    def registered_properties(self) -> set[PropertyPrefix]:
        pass

    @abstractmethod
    def register_config_property_type(self, prop, fallback: Optional[str] = None):
        pass

    def contains_property_prefix(self, property_prefix: PropertyPrefix):
        return property_prefix in self.registered_properties

    @classmethod
    def default_profile(cls) -> Profile:
        return cls._default_profile
