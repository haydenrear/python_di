import typing
from typing import Optional

import injector

from python_di.configs.di_util import DiUtilConstants, get_wrapped_fn, get_underlying
from python_di.inject.context_factory.context_factory import ComponentContextFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import ComponentFactoryInjectTypeMetadata, \
    ComponentSelfFactory, ComponentFactory
from python_util.logger.logger import LoggerFacade



def component(bind_to: list[type] = None,
              profile: typing.Union[str, None, list[str]] = None,
              priority: typing.Optional[int] = None,
              scope: Optional[injector.ScopeDecorator] = None):

    def class_decorator_inner(cls):
        binding = get_bindings(cls)
        self_factories = create_self_factories(cls, binding)
        cls.component_context_factory = True

        if isinstance(profile, list):
            for p in profile:
                c_factory = _get_c_factory(cls, p)
                self_factories.append(c_factory)
        elif isinstance(profile, str | None):
            c_factory = _get_c_factory(cls, profile)
            self_factories.append(c_factory)

        cls.context_factory = [ComponentContextFactory(self_factories)]

        return cls

    def _get_c_factory(cls, p):
        if hasattr(cls.__init__, '__bindings__'):
            c_factory = ComponentFactory.new_component_factory(cls, get_underlying(cls), p, priority, scope,
                                                               bind_to)
        else:
            c_factory = ComponentFactory.new_component_factory(cls, get_underlying(cls), profile, priority, scope,
                                                               bind_to)
        return c_factory

    def get_bindings(cls):
        binding = bind_to if bind_to is not None else [cls]
        if cls not in binding:
            binding.append(cls)
        return binding

    def create_self_factories(cls, bindings):
        component_self_factories: list[ComponentFactoryInjectTypeMetadata] = []
        underlying = get_underlying(cls)
        for class_property_name, class_property_method_value in cls.__dict__.items():
            if hasattr(cls, class_property_name):
                potential_self_bean_factory = getattr(cls, class_property_name)
                if (hasattr(potential_self_bean_factory, DiUtilConstants.wrapped_fn.name)
                        and hasattr(potential_self_bean_factory.wrapped_fn, 'self_factory')
                        and potential_self_bean_factory.wrapped_fn.self_factory):

                    self_bean_factory, wrapped = get_wrapped_fn(potential_self_bean_factory)
                    config_profile = self_bean_factory.profile
                    config_profile = retrieve_profiles(config_profile)

                    assert isinstance(config_profile, list)

                    for p in config_profile:
                        priority = self_bean_factory.priority
                        self_factory_scope = get_create_self_factory_scope(self_bean_factory)
                        LoggerFacade.info(f"Found bean self factory for {config_profile} and {cls}.")
                        factory = ComponentSelfFactory(cls, underlying, p, priority, self_factory_scope, wrapped,
                                                       bindings, self_bean_factory)
                        component_self_factories.append(factory)


        return component_self_factories

    def retrieve_profiles(config_profile):
        if config_profile is None:
            config_profile = [profile]
        elif isinstance(config_profile, str):
            config_profile = [config_profile]
        return config_profile

    def get_create_self_factory_scope(self_bean_factory):
        self_factory_scope = self_bean_factory.scope if self_bean_factory.scope is not None else None
        if self_factory_scope is None and scope is not None:
            self_factory_scope = scope
        if self_factory_scope is None:
            self_factory_scope = injector.singleton
        return self_factory_scope

    return class_decorator_inner
