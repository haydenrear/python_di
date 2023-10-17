import dataclasses
import importlib
import typing
from typing import Optional

import injector
from injector import Binder, CallableProvider

from python_di.configs.base_config import DiConfiguration
from python_di.configs.di_util import get_underlying, retrieve_callable_provider, \
    get_wrapped_fn, BeanFactoryProvider, add_subs
from python_di.configs.constants import DiUtilConstants
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.inject.inject_context_di import inject_context_di
from python_di.inject.prioritized_injectors import do_bind
from python_di.inject.inject_context import inject_context
from python_di.inject.injector_provider import RegisterableModuleT, InjectionContext
from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.file_parser import FileParser, retrieve_source_files
from python_di.reflect_scanner.graph_scanner import DecoratorOfGraphScanner, SubclassesOfGraphScannerArgs, \
    SubclassesOfGraphScanner, DecoratorOfGraphScannerArgs
from python_di.reflect_scanner.module_graph_models import GraphType
from python_util.reflection.reflection_utils import get_return_type, is_empty_inspect


def imported(configs: list[typing.Type], profile: Optional[str] = None):
    """
    Works from only having the import.
    :param configs:
    :param profile:
    :return:
    """

    def class_decorator_inner(cls):
        return cls

    return class_decorator_inner


def bean(profile: typing.Union[str, list[str], None] = None, priority: Optional[int] = None,
         type_id: Optional[str] = None, self_factory: bool = False,
         scope: Optional[typing.Type[injector.Scope]] = None):
    def bean_wrap(fn):
        fn, wrapped = get_wrapped_fn(fn)

        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        fn.is_bean = True
        fn.profile = profile
        fn.priority = priority
        fn.wrapped = wrapped
        fn.type_id = type_id
        fn.self_factory = self_factory
        fn.scope = scope if scope is not None else injector.singleton

        wrapper.wrapped_fn = fn

        return wrapper

    return bean_wrap


def lazy(fn):
    fn, wrapped = get_wrapped_fn(fn)

    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.wrapped_fn = fn
    fn.is_lazy = True
    fn.wrapped = wrapped
    return wrapper


class BuildableModule:

    def __init__(self, beans: list[(typing.Type, CallableProvider)] = None):
        self.beans_builder: list[(typing.Type, BeanFactoryProvider, typing.Type)] = beans if beans is not None else []

    def register_bean(self, bean_ty: typing.Type, provider: BeanFactoryProvider, scope):
        self.beans_builder.append((bean_ty, provider, scope))

    def build_beans(self, config: DiConfiguration) -> dict[str, RegisterableModuleT]:
        out_mods = {}
        for (i, b, s) in self.beans_builder:
            built_mod = b.build(config)
            for p, m in built_mod.items():
                if p in out_mods.keys():
                    out_mods[p].append((m, i, s))
                else:
                    out_mods[p] = [(m, i, s)]

        built_beans = {
            profile_name: self.configure_curry(bean_providers_for_profile)
            for profile_name, bean_providers_for_profile in out_mods.items()
        }

        return built_beans

    def configure_curry(self, bean_ty_cb: list[(typing.Type, CallableProvider, typing.Type)]) -> typing.Callable[
        [Binder], None]:
        return self.configure(bean_ty_cb)

    def configure(self, bean_ty_cb: list[(typing.Type, CallableProvider, typing.Type)]) -> typing.Callable[
        [Binder], None]:
        return lambda binder: self.create_binder(binder, bean_ty_cb)

    @staticmethod
    def create_binder(injector_value: injector.Binder, bean_ty_cb: list[(CallableProvider, typing.Type, typing.Type)]):
        for callable_provider, interface, scope in bean_ty_cb:
            do_bind(injector_value, interface, callable_provider, scope)


class TypeIdReturnType:
    # TODO: user provides a type for beans for which they cannot have a return type to use with injector.
    def __init__(self, type_id: str, ty_provider: typing.Callable[[], typing.Type]):
        self.type_id = type_id
        self.ty_provider = ty_provider


def get_config_clzz(underlying):
    if hasattr(underlying, DiUtilConstants.subs.name):
        for s in underlying.subs:
            if DiConfiguration in s.__bases__:
                return s
    return underlying


DiConfigurationT = typing.TypeVar("DiConfigurationT", covariant=True, bound=DiConfiguration)


@dataclasses.dataclass(init=True)
class ConfigurationFactory:
    di_config: typing.Type[DiConfigurationT]
    profile: Optional[str]
    priority: Optional[int]
    cls: typing.Type
    underlying: typing.Type


@inject_context_di()
def register_configuration(configuration_factory: ConfigurationFactory,
                           ctx: typing.Optional[InjectionContext] = None):
    ctx.register_configuration(configuration_factory.di_config,
                               configuration_factory.underlying,
                               configuration_factory.profile,
                               configuration_factory.priority,
                               [
                                   configuration_factory.cls,
                                   configuration_factory.di_config,
                                   configuration_factory.underlying
                               ])


def configuration(priority: Optional[int] = None, profile: Optional[str] = None):
    def class_decorator_inner(cls):
        underlying = get_underlying(cls)
        beans = BuildableModule()
        lazy_beans = BuildableModule()

        value = cls.__dict__.items()
        register_beans(beans, lazy_beans, value, profile)

        if cls != underlying:
            value = underlying.__dict__.items()
            register_beans(beans, lazy_beans, value, profile)

        class ClassConfiguration(DiConfiguration, cls):

            def lazy(self) -> dict[str, RegisterableModuleT]:
                return lazy_beans.build_beans(self)

            def initialize(self) -> dict[str, RegisterableModuleT]:
                return beans.build_beans(self)

        register_configuration(ConfigurationFactory(
            ClassConfiguration, profile, priority,
            cls, underlying
        ))

        add_subs(underlying, [ClassConfiguration, cls, DiConfiguration])

        return ClassConfiguration

    def register_beans(beans, lazy_beans, value, fallback_profile):
        for k, v in value:
            if hasattr(v, DiUtilConstants.wrapped_fn.name):
                v = getattr(v, DiUtilConstants.wrapped_fn.name)
                profile_found = retrieve_profile_if_exists(v, profile)
                if profile_found is None:
                    profile_found = fallback_profile
                scope = v.scope
                if hasattr(v, DiUtilConstants.is_bean.name):
                    return_type = get_return_type_from_fn(v)
                    if hasattr(v, DiUtilConstants.is_lazy.name):
                        lazy_beans.register_bean(return_type,
                                                 retrieve_callable_provider(v, profile_found),
                                                 scope)
                    else:
                        beans.register_bean(return_type,
                                            retrieve_callable_provider(v, profile_found),
                                            scope)

    def get_return_type_from_fn(v):
        return_type = get_return_type(v)
        if is_empty_inspect(return_type):
            if hasattr(v, DiUtilConstants.type_id.name):
                return v.type_id
        return return_type

    def retrieve_profile_if_exists(v, next_profile):
        if hasattr(v, DiUtilConstants.profile.name):
            return v.profile if v.profile is not None else next_profile

        return next_profile

    return class_decorator_inner


@inject_context()
def component_scan(base_packages: list[str] = None, configs: list[typing.Type] = None):
    inject = component_scan.inject_context()

    def class_decorator_inner(cls):
        underlying = get_underlying(cls)
        LoggerFacade.info(f"Found underlying: {underlying}.")

        class ComponentScanProxy(cls):
            LoggerFacade.info(f"Retrieving file parser underlying: {underlying}.")
            parser = inject.get_interface(SubclassesOfGraphScanner)
            decorator_scanner = inject.get_interface(DecoratorOfGraphScanner)
            if configs is not None:
                for c in configs:
                    underlying_c = get_underlying(cls)
                    inject.register_configuration(c, underlying_c)

            if base_packages is not None:
                for p in base_packages:
                    next_file_parser = inject.get_interface(FileParser, scope=injector.noscope)
                    if next_file_parser is None:
                        LoggerFacade.error("File parser could not be retrieved with no scope.")
                        break
                    source = retrieve_source_files(p)
                    parsed_file = next_file_parser.parse(source)
                    modules = parser.do_scan(SubclassesOfGraphScannerArgs(
                        injector.Module, parsed_file, GraphType.File
                    ))
                    for m in modules.nodes:
                        imported_mod = importlib.import_module(p)
                        if m.id_value in imported_mod.__dict__.keys():
                            found_value = imported_mod.__dict__[m.id_value]
                            LoggerFacade.info(f"Found injection module {found_value}")
                            inject.register_injector_from_module([found_value])
                    modules = decorator_scanner.do_scan(DecoratorOfGraphScannerArgs(
                        "configuration", parsed_file, GraphType.File
                    ))
                    for m in modules.nodes:
                        imported_mod = importlib.import_module(p)
                        found_value = imported_mod.__dict__[m.id_value]
                        LoggerFacade.info(f"Found configuration module {found_value}")

        ComponentScanProxy.proxied = underlying
        return ComponentScanProxy

    return class_decorator_inner


@dataclasses.dataclass(init=True)
class ConfigurationPropertiesFactory:
    config_props: typing.List[typing.Type[ConfigurationProperties]]
    cls: typing.Type


@inject_context_di()
def register_configuration_properties(config_factory: ConfigurationPropertiesFactory,
                                      ctx: typing.Optional[InjectionContext] = None):
    for c in config_factory.config_props:
        underlying = get_underlying(c)
        config_prop_created_other = ctx.get_interface(c)
        config_prop_created = ctx.get_interface(underlying)
        if config_prop_created is None and config_prop_created_other is not None:
            config_prop_created = config_prop_created_other

        if config_prop_created is None:
            if hasattr(underlying, DiUtilConstants.fallback.name):
                ctx.register_config_properties(c, underlying.fallback, bindings=[underlying])
            else:
                ctx.register_config_properties(c, bindings=[underlying])

            LoggerFacade.warn(f"Config properties {c} was not contained in injection context. Adding it "
                              f"without a fallback.")

            config_prop_created = ctx.get_interface(c)

            LoggerFacade.debug(f"Initialized {config_factory.cls}.")

            test_interface = ctx.get_interface(underlying)

            assert config_prop_created == test_interface, f"Binding to {c} failed for {underlying}."

        if config_prop_created is None:
            LoggerFacade.warn(f"Config properties {underlying} could not be added to context.")


def enable_configuration_properties(config_props: typing.List[typing.Type[ConfigurationProperties]]):
    def class_decorator_inner(cls):
        register_configuration_properties(ConfigurationPropertiesFactory(config_props, cls))
        return cls

    return class_decorator_inner
