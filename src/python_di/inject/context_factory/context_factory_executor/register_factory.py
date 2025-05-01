import typing
from types import TracebackType
from typing import Optional

import injector as injector

from python_di.configs.constants import DiUtilConstants, FnTy
from python_di.configs.di_util import get_underlying
from python_di.env.profile_config_props import ProfileProperties
from python_di.inject.context_factory.context_factory_executor.metadata_factory import MetadataFactory
from python_di.inject.context_factory.context_factory import PrototypeComponentFactory
from python_di.inject.context_factory.base_context_factory import CallableFactory
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import ConfigurationPropertiesInjectTypeMetadata, \
    ComponentSelfFactory, \
    ComponentFactory, BeanComponentFactory, LifecycleInjectTypeMetadata, MultibindTypeMetadata
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata, HasFnArgs
from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_di.inject.injector_provider import InjectionContextInjector, T
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.logger import LoggerFacade


def register_bean_component_factory(bean_component_factory: BeanComponentFactory,
                                    ctx: InjectionContextInjector):
    to_call_created = bean_component_factory.to_call
    ctx.register_component_binding(
        to_call_created,
        bean_component_factory.ty_to_inject,
        bean_component_factory.bindings if bean_component_factory.bindings is not None else [],
        bean_component_factory.scope, bean_component_factory.profile
    )


@inject_context_di()
def get_bean_dependency(bean_ty: typing.Type[T],
                        bean_scope: Optional[injector.ScopeDecorator] = None,
                        profile: Optional[str] = None,
                        ctx: Optional[InjectionContextInjector] = None):
    return ctx.get_interface(bean_ty, profile=profile, scope=bean_scope)


@inject_context_di()
def retrieve_factory(lifecycle_factory: CallableFactory,
                     metadata_factory: typing.Optional[MetadataFactory] = None,
                     ctx: Optional[InjectionContextInjector] = None):
    to_construct = {}
    do_inject = True
    v = lifecycle_factory.to_call

    items, profile = _deconstruct_inject_metadata(lifecycle_factory, metadata_factory, v)

    for key, val in items.items():
        if key == 'self' or key == 'args' or key == 'kwargs' or key == 'cls':
            continue
        try:
            LoggerFacade.debug(f"Retrieving bean: {val} for bean factory: {v} and profile {profile}.")
            from python_di.env.main_profile import DEFAULT_PROFILE
            from python_di.inject.profile_composite_injector.composite_injector import profile_scope
            found = ctx.get_interface(val, profile,
                                      scope=injector.singleton if profile is None or profile == DEFAULT_PROFILE
                                      else profile_scope)
            assert found is not None, f"{val} did not have registration for {profile}."
            to_construct[key] = found
        except AssertionError as e:
            raise e
        except Exception as e:
            LoggerFacade.error(f"Found error: {e}")
            LoggerFacade.warn(f"Failed to initialize test configuration {v} from getting {val}: {e}, "
                              f"{e.__traceback__}.")
            to_construct[key] = None
            do_inject = False
            break

    return do_inject, to_construct


def _deconstruct_inject_metadata(lifecycle_factory, metadata_factory, v):
    profile = metadata_factory.injectable_profile if metadata_factory is not None else None
    if profile is None and isinstance(lifecycle_factory, InjectTypeMetadata):
        profile = lifecycle_factory.profile
    if hasattr(v, DiUtilConstants.wrapped.name):
        items = getattr(v, DiUtilConstants.wrapped.name)
    else:
        if isinstance(lifecycle_factory, HasFnArgs):
            items = lifecycle_factory.fn_args
        else:
            items = {}
    return items, profile


def register_prototype_component_factory(component_factory_data: PrototypeComponentFactory,
                                         ctx: InjectionContextInjector):
    LoggerFacade.info(f"Registering {component_factory_data.ty_to_inject} as prototype scope.")
    ctx.register_component(component_factory_data.factory,
                           [component_factory_data.factory, component_factory_data.ty_to_inject],
                           # register the factory as singleton, as each bean dep can be in a different scope.
                           injector.singleton)


def do_lifecycle_hook(c: LifecycleInjectTypeMetadata,
                      ctx: InjectionContextInjector):
    to_call_value = c.to_call
    if c.lifecycle_type == FnTy.self_method:
        created_bean = ctx.get_interface(c.ty_to_inject, c.profile, c.scope)
        if created_bean is None:
            for b in c.bindings:
                created_bean = ctx.get_interface(b, c.profile, c.scope)
                if created_bean is not None:
                    break

        LoggerFacade.info(f"In lifecycle hook for {c.ty_to_inject} and {created_bean} is the new created bean.")
        args_to_inject = _get_args_to_inject(c, created_bean)
        to_call_value(**args_to_inject)
    elif c.lifecycle_type == FnTy.class_method:
        LoggerFacade.info(f"Calling {c.ty_to_inject} as lifecycle factory {c.__class__.__name__}.")
        args_to_inject = _get_args_to_inject(c, c.ty_to_inject)
        to_call_value(**args_to_inject)
    else:
        args_to_inject = _get_args_to_inject(c)
        to_call_value(**args_to_inject)


def _get_args_to_inject(c, created_bean=None, name='self'):
    args_callable = c.args_callable
    args_to_inject = args_callable()
    if args_to_inject is not None and created_bean is not None:
        args_to_inject[name] = created_bean
    elif args_to_inject is None:
        args_to_inject = {}
    return args_to_inject


@autowire_fn()
def register_component_factory(component_factory_data: ComponentFactory,
                               ctx: InjectionContextInjector,
                               profile_props: ProfileProperties):
    profile = component_factory_data.profile
    scope = component_factory_data.scope
    binding = component_factory_data.bindings
    cls = component_factory_data.ty_to_inject

    assert isinstance(component_factory_data, ComponentFactory)
    if isinstance(profile, list):
        assert scope == profile_scope
        for p in profile:
            ctx.register_component(cls, bindings=binding, scope=scope, profile=p)
    elif isinstance(profile, str):
        ctx.register_component(cls, binding, scope, profile)
        from python_di.env.main_profile import DEFAULT_PROFILE
        if profile != DEFAULT_PROFILE:
            assert scope is not None and scope != injector.singleton
            assert scope == profile_scope
            ctx.register_component(cls, binding, scope, DEFAULT_PROFILE)
    elif scope is None or scope == injector.singleton:
        ctx.register_component(cls, bindings=binding, scope=injector.singleton)
    elif scope == profile_scope and profile is None:
        ctx.register_component(cls, bindings=binding, scope=scope,
                               profile=profile_props.default_profile.profile_name)
    else:
        LoggerFacade.error(f"Error registering {component_factory_data.ty_to_inject}. Did not match eligibility "
                           f"criteria for registration.")


def register_component_self_factory(component_factory_data: ComponentSelfFactory,
                                    ctx: InjectionContextInjector):
    assert isinstance(component_factory_data, ComponentSelfFactory)
    f: ComponentSelfFactory = component_factory_data
    cls = f.ty_to_inject
    ctx.register_component_binding(lambda: do_call(f, cls),
                                   cls, f.bindings, f.scope, f.profile)


def register_multibind_factory(component_factory_data: MultibindTypeMetadata,
                               ctx: InjectionContextInjector):
    assert isinstance(component_factory_data, MultibindTypeMetadata)
    ctx.register_component_multibinding(_do_multibind_curry(component_factory_data.scope,
                                                            component_factory_data.profile,
                                                            component_factory_data.bindings),
                                        component_factory_data.ty_to_inject,
                                        component_factory_data.scope,
                                        component_factory_data.profile)


def _do_multibind_curry(scope, profile, bindings) -> typing.Callable:
    return lambda: _do_multibind(scope, profile, bindings)


@inject_context_di()
def _do_multibind(scope, profile, bindings, ctx: Optional[InjectionContextInjector] = None):
    return [
        ctx.get_interface(b, profile=profile, scope=scope) for b in bindings
    ]


def do_call(f, cls):
    _, factory_retrieved = retrieve_factory(f)
    to_callable = f.to_call
    return to_callable(cls, **factory_retrieved)


def register_configuration_properties(config_factory: ConfigurationPropertiesInjectTypeMetadata,
                                      ctx: InjectionContextInjector):
    c = config_factory.ty_to_inject
    underlying = get_underlying(c)

    config_prop_created_other = ctx.get_interface(c)
    config_prop_created = ctx.get_interface(underlying)

    if config_prop_created is None and config_prop_created_other is not None:
        config_prop_created = config_prop_created_other

    if config_prop_created is None:
        LoggerFacade.info(f"Registering {c} from {config_factory}")
        if hasattr(underlying, DiUtilConstants.fallback.name):
            ctx.register_config_properties(c, underlying.fallback, bindings=[underlying])
        else:
            ctx.register_config_properties(c, bindings=[underlying])

        LoggerFacade.warn(f"Config properties {c} was not contained in injection context. Adding it "
                          f"without a fallback.")

        config_prop_created = ctx.get_interface(c)

        LoggerFacade.debug(f"Initialized {config_factory.ty_to_inject}.")

        test_interface = ctx.get_interface(underlying)

        assert config_prop_created == test_interface, f"Binding to {c} failed for {underlying}."

    if config_prop_created is None:
        LoggerFacade.warn(f"Config properties {underlying} could not be added to context.")
