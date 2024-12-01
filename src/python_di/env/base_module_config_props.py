import abc
import typing
from abc import ABC

from pydantic import BaseModel

from python_util.logger.logger import LoggerFacade

ConfigurationPropertiesT = typing.ForwardRef("ConfigurationProperties")


class ConfigurationProperties(BaseModel, ABC):

    def retrieve_prop(self, prop_name: str):
        return getattr(self, prop_name)

    def attrs(self) -> set[str]:
        return self.__fields_set__

    def merge_with(self, other: ConfigurationPropertiesT):
        other: ConfigurationProperties = other
        for v in self.__fields_set__:
            assert hasattr(other, v)
            this_value = getattr(other, v)
            other_value = getattr(self, v)
            if this_value != other_value and this_value is not None:
                LoggerFacade.warn(f"Retrieved conflicting properties in {self.__class__.__name__}. {v} was set to be "
                                  f"both {this_value} and {other_value}. Set to {this_value}.")
            elif this_value is None:
                setattr(self, v, other_value)


class BaseModuleProps(ConfigurationProperties, abc.ABC):
    pass

