import asyncio
import collections
import os
import typing
import uuid
from typing import Optional

import yaml

from python_util.collections.collection_util import collect_multimap
from python_di.env.base_env_properties import PropertyPrefix, Environment
from python_di.env.main_profile import DEFAULT_PROFILE
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.env_factories import Factories, Factory
from python_di.env.init_env import import_load
from python_di.env.profile import Profile
from python_di.env.profile_config_props import ProfileProperties
from python_di.env.properties_loader import PropertyLoader
from python_di.env.property_source import PropertySource
from python_di.inject.injector_provider import ConfigPropsT
from python_util.logger.logger import LoggerFacade

Priority = int

YAML_ENV_PROFILE: str = 'yaml_profile'
YAML_ENV_PRIORITY: int = 1


class YamlPropertiesFilesBasedEnvironment(Environment):

    def __init__(self):
        self._profiles: Optional[ProfileProperties] = None
        self._factories: Optional[Factories] = None
        self._factories_locks: dict[str, asyncio.Event] = {}
        for k, v in os.environ.items():
            LoggerFacade.info(f'{k}: {v}')
        if "RESOURCES_DIR" in os.environ.keys():
            self.resources_dir = os.environ["RESOURCES_DIR"]
        elif "PROJ_HOME" in os.environ.keys():
            join = os.path.join(os.environ["PROJ_HOME"], "resources")
            self.resources_dir = join
        else:
            self.resources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")

        self.yml_files = self.get_yml_files(self.resources_dir)

        LoggerFacade.info(f"Initializing properties loader for yaml files: {self.yml_files}.")
        self.properties_loaders: dict[str, PropertyLoader] = {
            yml_file: PropertyLoader(yml_file) for yml_file
            in self.yml_files
        }

        self._config_properties: typing.OrderedDict[Profile, PropertySource] = collections.OrderedDict({})
        self._registered_properties: set[PropertyPrefix] = set([])
        self._self_profile = Profile.new_profile(YAML_ENV_PROFILE, 1)

        self.load_factories_from_yml()

    @classmethod
    def collect_multimap_partition_by(cls, factory: (str, Factory)):
        return factory[0]

    def register_config_property_values(self, property_values: ConfigPropsT,
                                        profile: Optional[str] = None,
                                        priority: Optional[int] = None,
                                        prefix_name: Optional[str] = None):
        if prefix_name is not None:
            self.registered_properties.add(prefix_name)
        if profile is not None:
            profile = self.profiles.create_get_profile_name_priority(priority, profile)
            props = self.create_get_props(profile)
        elif priority is not None:
            profile = self.profiles.create_get_profile_name_priority(priority)
            props = self.create_get_props(profile)
        else:
            profile = self.default_profile()
            props = PropertySource(profile)

        if profile not in self.config_properties.keys():
            self.config_properties[profile] = props

        if isinstance(property_values, dict):
            for k, v in property_values.items():
                props.add_dyn_prop(k, v)
                self.registered_properties.add(f'{prefix_name}.{k}')
        else:
            if isinstance(property_values, PropertySource):
                props.merge_config_props(property_values)
                self._register_property_source_props(prefix_name, property_values)
            elif isinstance(property_values, ConfigurationProperties):
                for attr in property_values.attrs():
                    value = getattr(property_values, attr)
                    props.add_dyn_prop(attr, value)
                    self._register_prop(attr, prefix_name)
            else:
                LoggerFacade.error(f"Could not read property values of type {type(property_values)}.")

    def _register_property_source_props(self, prefix_name, property_values):
        for p in property_values.rev_idx.keys():
            self._register_prop(p, prefix_name)
        for p in property_values.other_properties.keys():
            self._register_prop(p, prefix_name)

    def _register_prop(self, p, prefix_name):
        next_prop_added = f'{prefix_name}.{p}' if prefix_name is not None else p
        self.registered_properties.add(next_prop_added)

    def create_get_props(self, profile):
        if profile in self.config_properties.keys():
            props = self.config_properties[profile]
        else:
            props = PropertySource(profile)
            self.config_properties[profile] = props
        return props


    def load_factories(self, lazy):
        if self.factories is not None and self.factories.factories is not None:
            for factory in self.factories.factories:
                if lazy and factory.lazy:
                    loaded = self._do_initialize(factory)
                    if loaded is not None:
                        yield loaded
                elif not lazy and not factory.lazy:
                    loaded = self._do_initialize(factory)
                    if loaded is not None:
                        yield loaded

    def _do_initialize(self, factory: Factory):
        if not self._factories_locks[factory.factory].is_set():
            out = import_load(factory.factory)
            self._factories_locks[factory.factory].set()
            return out

    def retrieve_profile(self, profile_name: str) -> Optional[Profile]:
        if self.profiles:
            for p_name, p in self.profiles.active_profiles.items():
                if profile_name == p_name:
                    return p

        for p in self.config_properties.keys():
            if p.profile_name == profile_name:
                return p


    @property
    def registered_properties(self) -> set[PropertyPrefix]:
        return self._registered_properties

    @property
    def profiles(self):
        return self._profiles

    @profiles.setter
    def profiles(self, profiles: ProfileProperties):
        self._profiles = profiles
        for p in self.profiles_iter():
            if p not in self.config_properties.keys():
                self.config_properties[p] = PropertySource(p)

        default_profile = self.default_profile()
        if default_profile not in self.config_properties.keys():
            self.config_properties[default_profile] = PropertySource(default_profile)

    @property
    def config_properties(self):
        return self._config_properties

    @config_properties.setter
    def config_properties(self, config_properties: list[PropertySource]):
        if len(self._config_properties) != 0:
            self._config_properties.extend(config_properties)
        else:
            self._config_properties = config_properties

    @property
    def factories(self):
        return self._factories

    @factories.setter
    def factories(self, factories: Factories):
        self._factories = factories

    @staticmethod
    def get_yml_files(join):
        yml_files = []
        if not os.path.exists(join):
            raise Exception("Project home existed, but resources path did not exist.")
        for file in os.listdir(join):
            if os.path.isfile(os.path.join(join, file)) and os.path.basename(file).endswith('.yml') \
                    or os.path.basename(file).endswith('.yaml'):
                yml_files.append(os.path.join(join, file))
        return [i for i in  sorted(yml_files, key=lambda x: len(x))]

    def load_prop_recursive(self, properties: dict, props, prev):
        if isinstance(props, dict):
            for prop_key, property in props.items():
                self.load_prop_recursive(properties, property, f'{prev}.{prop_key}')
        else:
            properties[prev] = props

    def load_factories_from_yml(self):
        for yml_file in self.yml_files:
            with open(f"{yml_file}", "r") as props:
                try:
                    props = yaml.safe_load(props)
                except Exception as e:
                    LoggerFacade.error(f"Error loading yml file {yml_file} with error {e}")
                    continue
                for prop, prop_value in props.items():
                    if prop == "env_factories":
                        try:
                            next_factories: Factories = self.properties_loaders[yml_file].load_property_by_ty(
                                Factories, "env_factories")
                            if self._factories is None or len(self._factories.factories) == 0:
                                self._factories = next_factories
                            else:
                                for v in next_factories.factories:
                                    if v.factory not in self._factories.factories:
                                        self._factories.factories.append(v)
                                    else:
                                        LoggerFacade.error(f"Found factory with key {v.factory} that already existed.")
                            for f in [s for s in next_factories.factories]:
                                if f.factory not in self._factories_locks.keys():
                                    self._factories_locks[f.factory] = asyncio.Event()
                        except Exception as e:
                            LoggerFacade.error(f"Error loading factories from {yml_file} with error {e}.")

    @staticmethod
    def get_profile_from_yml(yml_name: str):
        basename = os.path.basename(yml_name)
        if 'application-' in basename and not basename.endswith('application.yml'):
            splitted = basename.split('application-')
            if len(splitted) == 2:
                s = splitted[1].split('.yml')
                YamlPropertiesFilesBasedEnvironment.log_profile_name(s[0], yml_name)
                return s[0]
        YamlPropertiesFilesBasedEnvironment.log_profile_name(DEFAULT_PROFILE, yml_name)
        return DEFAULT_PROFILE

    @staticmethod
    def log_profile_name(profile_name, yml_name):
        LoggerFacade.debug(f"Retrieved {profile_name} as profile name for {yml_name}.")

    @staticmethod
    def calculate_precedence() -> Priority:
        return 0

    def load_profiles_from_env(self):
        if 'spring.profiles.active' in os.environ.keys():
            return self.parse_profiles_from_profile_env(os.environ['spring.profiles.active'])
        if "SPRING_PROFILES_ACTIVE" in os.environ.keys():
            return self.parse_profiles_from_profile_env(os.environ['SPRING_PROFILES_ACTIVE'])


    @staticmethod
    def parse_profiles_from_profile_env(p):
        p = [p.strip() for p in p.split(',')]
        if len(p) != 0:
            default = list(reversed(p))[0]
            return ProfileProperties(**{
                "active_profiles": {profile_name: Profile(**{"profile_name": p, "priority": i})
                                    for i, profile_name in enumerate(p)},
                "default_profile": Profile(**{"profile_name": default, "priority": len(p) - 1})
            })

    def get_sorted_yml_files(self):
        sorted_profiles: list[Profile] = self.profiles.profiles_sorted_by_priority()
        sorted_yml_files = []
        for s_value in sorted_profiles:
            for y in self.yml_files:
                if s_value.profile_name == 'main_profile':
                    if y.endswith('application.yml') or y.endswith('application-main.yml'):
                        sorted_yml_files.append(y)
                        break
                elif y.endswith(f'{s_value.profile_name}.yml'):
                    sorted_yml_files.append(y)
                    break

        for y in self.yml_files:
            if y not in sorted_yml_files:
                sorted_yml_files.append(y)

        return sorted_yml_files

    def load_props_for_tys(self,
                           ty: type[ConfigurationProperties],
                           fallback: Optional[str] = None) -> ConfigurationProperties:
        self.assert_prefixname(ty)
        yml_files = self.get_sorted_yml_files()
        return self._load_props_for_tys(yml_files, ty, fallback)

    def load_profiles(self, fallback: Optional[str] = None) -> ConfigurationProperties:
        from_env = self.load_profiles_from_env()
        if from_env is not None:
            return from_env
        else:
            ty = ProfileProperties
            self.assert_prefixname(ty)
            return self._load_profile_properties(self.yml_files, fallback)

    def _load_profile_properties(self,
                                 yml_files,
                                 fallback: Optional[str] = None) -> typing.Optional[ConfigurationProperties]:
        for yml_file in yml_files:
            load_props = self._do_register_add_profile(yml_file)
            if load_props is not None:
                return load_props
        if fallback is not None and os.path.exists(fallback):
            LoggerFacade.warn(f"No properties provided for {ProfileProperties}. Using fallback: {fallback}.")
            return self._do_register_add_profile(fallback)
        else:
            LoggerFacade.error(f"No properties provided for {ProfileProperties}. Tried using fallback {fallback} "
                               f"but fallback did not exist.")

    def _load_props_for_tys(self,
                           yml_files,
                           ty: type[ConfigurationProperties],
                           fallback: Optional[str] = None) -> typing.Optional[ConfigurationProperties]:
        prefix_name = ty.prefix_name
        for yml_file in yml_files:
            profile_name = self.get_profile_from_yml(yml_file)
            profile = self.retrieve_profile(profile_name)
            if profile_name not in self.config_properties:
                if profile is not None and profile not in self.config_properties.keys():
                    self.config_properties[profile] = PropertySource(profile)
                else:
                    LoggerFacade.warn(
                        f"Retrieved properties for profile {profile_name} that did not exist in profiles.")
                    profile = self.default_profile()
                    if profile not in self.config_properties.keys():
                        self.config_properties[profile] = PropertySource(profile)

            load_props = self._do_register_add_props(ty, yml_file, prefix_name, profile)
            if load_props is not None:
                return load_props
        if fallback is not None and os.path.exists(fallback):
            LoggerFacade.warn(f"No properties provided for {ty}. Using fallback: {fallback}.")
            return self._do_register_add_props(ty, fallback, prefix_name, self.default_profile())
        else:
            LoggerFacade.error(f"No properties provided for {ty}. Tried using fallback {fallback} "
                               f"but fallback did not exist.")

    def assert_prefixname(self, ty):
        from python_di.configs.constants import DiUtilConstants
        assert hasattr(ty, DiUtilConstants.prefix_name.name), (f"Configuration property {ty} was supposed to have "
                                                               f"prefix name.")

    def _do_register_add_profile(self, yml_file: str) -> Optional:
        with open(f"{yml_file}", "r") as props:
            props = yaml.safe_load(props)
            for prop, prop_value in props.items():
                if prop == 'profiles':
                    if yml_file not in self.properties_loaders.keys():
                        self.properties_loaders[yml_file] = PropertyLoader(yml_file)
                    by_ty = self.properties_loaders[yml_file].load_property_by_ty(ProfileProperties, 'profiles')
                    assert by_ty is not None, (f"profiles had property that was None for {ProfileProperties} and {yml_file}. "
                                               f"There may be a property missing.")
                    LoggerFacade.info(f"Successfully loaded props: profiles from {yml_file}.")
                    self.config_properties[Environment.default_profile()] = PropertySource(Environment.default_profile())
                    self.config_properties[Environment.default_profile()].add_config_property('profiles', by_ty)
                    self.registered_properties.add('profiles')
                    return by_ty



    def _do_register_add_props(self, ty: type[ConfigurationProperties], yml_file: str,
                               prefix_name: str, profile_name: Profile) -> Optional:
        with open(f"{yml_file}", "r") as props:
            props = yaml.safe_load(props)
            for prop, prop_value in props.items():
                if prop == prefix_name:
                    if yml_file not in self.properties_loaders.keys():
                        self.properties_loaders[yml_file] = PropertyLoader(yml_file)
                    by_ty = self.properties_loaders[yml_file].load_property_by_ty(ty, prefix_name)
                    assert by_ty is not None, (f"{prefix_name} had property that was None for {ty} and {yml_file}. "
                                               f"There may be a property missing.")
                    if profile_name not in self.config_properties.keys():
                        LoggerFacade.debug(f"Creating config property for {profile_name}: {by_ty}.")
                        self.config_properties[profile_name] = PropertySource(profile_name)
                        self.config_properties[profile_name].add_config_property(prefix_name, by_ty)
                    else:
                        LoggerFacade.debug(f"Merging config property for {profile_name}: {by_ty} with "
                                           f"{self.config_properties[profile_name]}.")
                        self.config_properties[profile_name].merge_configuration_property(prefix_name, by_ty)
                    self.registered_properties.add(prefix_name)
                    LoggerFacade.info(f"Successfully loaded props: {prefix_name} from {yml_file}.")
                    return by_ty
                else:
                    LoggerFacade.debug(f"Parsed {prop} but did not add because did not load as config prop.")

    def load_prop_ty(self, ty: type[ConfigurationProperties],
                     profile: Optional[Profile] = None):
        self.assert_prefixname(ty)
        prefix_name = ty.prefix_name
        if not self.contains_property_prefix(prefix_name):
            return None
        if profile is not None:
            if profile in self.config_properties.keys() and self.config_properties[profile].contains_prefix(
                    prefix_name):
                return self.config_properties[profile].get_config_prop(prefix_name)
            else:
                return self.highest_priority_source(prefix_name)

    def highest_priority_source(self, prefix_name):
        for profile, prop in self.config_properties.items():
            if prop.contains_prefix(prefix_name):
                return prop

    def register_config_property_type(self, prop: type[ConfigurationProperties],
                                      fallback: Optional[str] = None) -> ConfigurationProperties:
        out = self.load_props_for_tys(prop, fallback)
        return out

    def register_profiles_config(self, fallback: Optional[str] = None) -> ConfigurationProperties:
        out = self.load_profiles(fallback)
        return out

    def get_property(self, key, profile: Optional[str] = None) -> Optional[object]:
        profile_found = self.retrieve_profile(profile)
        if profile_found in self.config_properties.keys():
            found_property_source = self.config_properties[profile_found]
            out_prop = found_property_source.get_prop(key)
            if out_prop is not None:
                return out_prop
        if self.profiles is not None:
            for p in self.profiles_iter():
                if p in self.config_properties.keys():
                    found_property_source = self.config_properties[p]
                    out_prop = found_property_source.get_prop(key)
                    if out_prop is not None:
                        return out_prop
        else:
            LoggerFacade.warn(f"Profiles was not set before property {key} from profile {profile} was requested.")
        if self.config_properties is not None:
            for p in self.config_properties.values():
                value = p.get_prop(key)
                if value is not None:
                    return value
        else:
            LoggerFacade.warn(f"Config properties was not set before property {key} from profile {profile} was "
                              f"requested.")

        return None

    def profiles_iter(self):
        return sorted(self.profiles.active_profiles.values(), reverse=True)

    def set_property(self, key: str, value: object, profile: Optional[str] = None):
        if profile is not None:
            profile_found = self.retrieve_profile(profile)
            if profile_found is not None:
                self.config_properties[profile_found].add_dyn_prop(key, value)
        else:
            profile_found = self.default_profile()
            if profile_found is not None:
                self.config_properties[profile_found].add_dyn_prop(key, value)

    def get_property_with_default(self, key: str, default: str, profile: Optional[str] = None) -> object:
        prop = self.get_property(key, profile)
        return prop if prop else default

    @property
    def self_profile(self) -> Profile:
        return self._self_profile
