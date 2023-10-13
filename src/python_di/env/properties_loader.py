import typing

import yaml
from pydantic.error_wrappers import ValidationError
from pydantic.main import BaseModel

from python_util.logger.logger import LoggerFacade


class MissingPrefixException(Exception):
    pass


class PropertyLoader:
    def __init__(self, yaml_path: str):
        self._yaml_path = yaml_path
        self._properties = {}
        self.load_properties()

    def load_property_by_ty(self, input_ty: typing.Type[BaseModel],
                            prefix: str):
        properties = self.get_properties_by_prefix(prefix)
        try:
            inputted = input_ty(**properties)
            return inputted
        except ValidationError as e:
            LoggerFacade.error(e.errors())

    def load_properties(self):
        with open(self._yaml_path, "r") as file:
            self._properties = yaml.safe_load(file)

    def get_properties_by_prefix(self, prefix: str) -> dict:
        if prefix in self._properties:
            return self._properties[prefix]
        raise MissingPrefixException(f"Prefix '{prefix}' not found in the YAML file.")
