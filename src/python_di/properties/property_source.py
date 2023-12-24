import typing
from typing import Optional

from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_di.inject.injector_provider import InjectionContextInjector


@inject_context_di()
def property_source(props: dict[str, object] = None,
                    prefix_name: Optional[str] = None,
                    profile_name: Optional[str] = None,
                    priority: Optional[int] = None,
                    ctx: typing.Optional[InjectionContextInjector] = None):
    ctx.register_config_property_values(props, profile_name, priority, prefix_name)

    def property_source_proxy(cls):
        return cls

    return property_source_proxy


def test_property_source(props: dict[str, object] = None, prefix_name: Optional[str] = None):
    return property_source(props, prefix_name, 'test_precedence', 1000)
