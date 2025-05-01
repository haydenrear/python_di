import os.path
from typing import Optional

from python_util.logger.logger import LoggerFacade


class ConfigurationPropsMarker:
    pass


def configuration_properties(prefix_name: Optional[str] = None,
                             fallback: Optional[str] = None):

    if fallback is not None and not os.path.exists(fallback):
        LoggerFacade.error(f"Error: {fallback} did not exist when creating properties with prefix {prefix_name}.")

    def class_decorator_inner(cls):
        from python_di.configs.di_util import get_underlying
        underlying = get_underlying(cls)
        underlying.fallback = fallback
        underlying.prefix_name = prefix_name
        underlying.eager = True
        cls.fallback = fallback
        cls.prefix_name = prefix_name
        cls.eager = True
        cls.prefix_name = prefix_name
        return cls

    return class_decorator_inner
