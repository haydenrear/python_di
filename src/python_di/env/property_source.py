import typing
from typing import Optional

import pydantic

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.env.profile import Profile
from python_util.logger.logger import LoggerFacade
from python_util.ordered.ordering import Ordered

PropertySourceT = typing.ForwardRef("PropertySource")


class PropertySource(Ordered):

    def __init__(self, profile: Profile,
                 config_properties: dict[str, ConfigurationProperties] = None,
                 other_properties: dict[str, object] = None,
                 secrets_overrides = None):
        self.secrets_overrides = secrets_overrides if secrets_overrides else {}
        self.other_properties = other_properties if other_properties is not None else {}
        self.profile = profile
        self._config_properties = config_properties if config_properties is not None else {}
        self.idx = {
            k: p.attrs() for k, p in self._config_properties.items()
        }
        self.rev_idx = {
            prop: k for k, p in self._config_properties.items()
            for prop in p.attrs()
        }

    def merge_with(self, other: PropertySourceT):
        assert other.profile == self.profile
        other: PropertySource = other
        if len(other._config_properties) != 0:
            self.merge_config_props(other)
        if len(other.other_properties) != 0:
            self.merge_other_props(other)

    def merge_other_props(self, other):
        for k, v in other.other_properties.items():
            if k not in self.other_properties.keys():
                self.other_properties[k] = v

    def merge_config_props(self, other):
        for k, v in other._config_properties:
            v: ConfigurationProperties = v
            if k not in self._config_properties.keys():
                self.add_config_property(k, v)

    def contains_prefix(self, prefix_name: str):
        return prefix_name in self._config_properties.keys()

    def merge_configuration_property(self, key: str, config_prop: ConfigurationProperties):
        """
        Where the current config does not contain a property, set the property.
        :param key:
        :param config_prop:
        :return:
        """
        if key not in self._config_properties.keys():
            self.add_config_property(key, config_prop)
        else:
            curr = self._config_properties[key]
            for attr in config_prop.attrs():
                if curr.retrieve_prop(attr) is None:
                    potential_new = config_prop.retrieve_prop(attr)
                    if potential_new is not None:
                        setattr(curr, attr, potential_new)
                    self.add_new_prop(key, attr)

    def add_new_prop(self, key: str, prop_key: str):
        if key not in self.idx.keys():
            self.idx[key] = [prop_key]
        else:
            self.idx[key].add(prop_key)

        self.rev_idx[prop_key] = key


    def add_config_property(self, key: str, config_prop: ConfigurationProperties):
        assert key not in self._config_properties.keys(), f"Configuration property already contained with key {key}."

        self._do_set_secrets(config_prop)

        self._config_properties[key] = config_prop
        self.idx[key] = config_prop.attrs()
        self.log_add_prop(key, config_prop)
        for c in config_prop.attrs():
            if c in self.rev_idx.keys():
                LoggerFacade.warn(f"Configuration property {config_prop} already contained with "
                                  f"key {key} when checking {c}.")
            else:
                self.rev_idx[c] = key

    def _do_set_secrets(self, config_prop: pydantic.BaseModel):
        for f, model_found in config_prop.model_fields.items():
            model_found = getattr(config_prop, f)
            if isinstance(model_found, str | int | float):
                if '{{X_' in model_found:
                    split = next(iter([i for i in model_found.split('{{') if i.startswith('X_')]))
                    split = next(iter([i for i in split.split('}}') if i.startswith('X_')]))
                    if split in self.secrets_overrides.keys():
                        LoggerFacade.debug(f"Replacing {model_found}")
                        model_found = model_found.replace('{{', '') .replace('}}', '')
                        model_found = model_found.replace(split, self.secrets_overrides.get(model_found))
                        setattr(config_prop, f, model_found)
            elif isinstance(model_found, pydantic.BaseModel):
                self._do_set_secrets(model_found)

    def add_dyn_prop(self, key: str, value: object):
        if isinstance(value, pydantic.BaseModel):
            self._do_set_secrets(value)

        self.log_add_prop(key, value)
        self.other_properties[key] = value

    def log_add_prop(self, key, value):
        LoggerFacade.debug(f"Adding property\nkey: {key}\nvalue: {value}\nto profile: \n{self.profile}.")

    def order(self) -> int:
        return self.profile.priority

    def get_config_prop(self, key) -> Optional:
        if key in self._config_properties.keys():
            return self._config_properties[key]
        elif key in self.other_properties.keys():
            return self.other_properties[key]

    def get_prop(self, key) -> Optional:
        if key in self._config_properties.keys():
            return self._config_properties[key]
        else:
            if key in self.rev_idx.keys():
                idx = self.rev_idx[key]
                assert idx in self._config_properties, f"{idx} was not contained in config properties."
                prop_found = self._config_properties[idx].retrieve_prop(key)
                if prop_found is not None:
                    return prop_found
            elif key in self.other_properties.keys():
                return self.other_properties[key]
