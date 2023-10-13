import os.path
from typing import Optional

from pydantic.main import BaseModel

from python_di.configs.constructable import ConstructableMarker
from python_di.inject.inject_context import inject_context
from python_util.logger.logger import LoggerFacade
from python_util.reflection.reflection_utils import get_fn_param_types


class ConfigurationPropsMarker:
    pass


@inject_context()
def configuration_properties(prefix_name: Optional[str] = None,
                             fallback: Optional[str] = None):
    inject = configuration_properties.inject_context()

    if fallback is not None and not os.path.exists(fallback):
        LoggerFacade.error(f"Error: {fallback} did not exist when creating properties with prefix {prefix_name}.")

    def class_decorator_inner(cls):

        from python_di.configs.di_util import get_underlying, add_subs, call_constructable
        underlying = get_underlying(cls)
        underlying.fallback = fallback
        underlying.prefix_name = prefix_name
        underlying.eager = True

        class ConfigurationPropertiesWrapper(cls):
            cls.prefix_name = prefix_name

            def __init__(self, **kwargs):
                call_constructable(underlying, self, ConfigurationPropertiesWrapper, **kwargs)
                if kwargs is not None and isinstance(self, BaseModel):
                    try:
                        BaseModel.__init__(self, **kwargs)
                    except Exception as e:
                        LoggerFacade.error(f'Failed to create {cls} from base model with kwargs {kwargs}, with '
                                           f'error: {e}')
                        raise e
                else:
                    out = get_fn_param_types(cls.__init__)
                    params = []
                    for name, (value, default_val) in out.items():
                        created_param = inject.get_interface(value)
                        if created_param:
                            params.append(created_param)
                        else:
                            if prefix_name:
                                default_value = inject.get_property_with_default(f'{prefix_name}.{name}',
                                                                                 default_val)
                                params.append(default_value)
                            else:
                                default_value = inject.get_property_with_default(f'{name}', default_val)
                                params.append(default_value)
                    cls.__init__(*params)

        add_subs(underlying, [{ConstructableMarker: ConfigurationPropertiesWrapper}])
        ConfigurationPropertiesWrapper.proxied = underlying

        return ConfigurationPropertiesWrapper

    return class_decorator_inner
