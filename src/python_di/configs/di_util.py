import copy
import typing

import injector

import python_util.reflection.reflection_utils
from python_di.configs.base_config import DiConfiguration
from python_di.configs.constants import DiUtilConstants
from python_di.configs.constructable import ConstructableMarker
from python_di.inject.composite_injector import profile_scope
from python_di.inject.inject_context import inject_context
from python_util.logger.logger import LoggerFacade
from python_util.reflection.reflection_utils import get_all_fn_param_types_no_default


def get_wrapped_fn(fn):
    if hasattr(fn, DiUtilConstants.wrapped_fn.name):
        fn = getattr(fn, DiUtilConstants.wrapped_fn.name)
    wrapped = {i: v for i, v in get_all_fn_param_types_no_default(fn).items()
               if i != 'self' and i != 'args' and i != 'kwargs'}
    return fn, wrapped


def get_underlying(cls):
    if hasattr(cls, DiUtilConstants.proxied.name):
        return getattr(cls, DiUtilConstants.proxied.name)
    else:
        cls.proxied = cls
    return cls


class BeanFactoryProvider:

    def __init__(self, value: typing.Callable[[DiConfiguration, str], injector.CallableProvider],
                 profile: typing.Union[str, list[str], None]):
        self.profile = profile
        self.value = value

    def build(self, config: DiConfiguration) -> dict[str, injector.CallableProvider]:
        from python_di.env.env_properties import DEFAULT_PROFILE
        if isinstance(self.profile, list):
            out_cb = {p: self.value(config, p) for p in self.profile}
        elif isinstance(self.profile, str):
            out_cb = {self.profile: self.value(config, self.profile)}
        else:
            out_cb = {DEFAULT_PROFILE: self.value(config, DEFAULT_PROFILE)}
        if DEFAULT_PROFILE not in out_cb.keys():
            out_cb[DEFAULT_PROFILE] = self.value(config, DEFAULT_PROFILE)

        return out_cb


def retrieve_callable_provider(v, profile) -> BeanFactoryProvider:
    return BeanFactoryProvider(lambda config, profile_created: create_callable_provider_curry(v, profile_created,
                                                                                              config),
                               profile)


def create_callable_provider_curry(v, profile, config):
    return injector.CallableProvider(lambda: v(**create_callable_provider(v, profile, config)))


def create_callable_provider(v, profile, config):
    do_inject, to_construct_factories = retrieve_factory(v, profile)
    provider_created = to_construct_factories
    provider_created['self'] = config
    return provider_created


@inject_context()
def retrieve_factory(v, profile):
    inject = retrieve_factory.inject_context()
    to_construct = {}
    do_inject = True
    items = getattr(v, DiUtilConstants.wrapped.name).items()
    for key, val in items:
        if key == 'self' or key == 'args' or key == 'kwargs' or key == 'cls':
            continue
        try:
            LoggerFacade.info(f"Retrieving bean: {val} for bean factory: {v}.")
            from python_di.env.env_properties import DEFAULT_PROFILE
            found = inject.get_interface(val, profile,
                                         scope=injector.singleton if profile is None or profile == DEFAULT_PROFILE
                                         else profile_scope)
            assert found is not None
            to_construct[key] = found
        except Exception as e:
            LoggerFacade.warn(f"Failed to initialize test configuration {v} from getting {val}: {e}.")
            to_construct[key] = None
            do_inject = False
            break
    return do_inject, to_construct


def get_constructable(tys):
    count = 0
    for ty in tys:
        if isinstance(ty, dict) and ConstructableMarker in ty.keys():
            return ty, count
        count += 1
    return None, None


def add_constructable(underlying, constructable):
    if hasattr(underlying, DiUtilConstants.subs.name):
        for t in underlying.subs:
            if isinstance(t, dict) and ConstructableMarker in t.keys():
                LoggerFacade.info(f"Adding constructable {t}.")
                t[ConstructableMarker].append(constructable[ConstructableMarker])


def add_subs(underlying, tys: list):
    constructable, idx = get_constructable(tys)
    if constructable is not None:
        add_constructable(underlying, tys)
        tys.pop(idx)
    if hasattr(underlying, DiUtilConstants.subs.name):
        for t in tys:
            underlying.subs.append(t)
    else:
        underlying.subs = tys


def add_attr(underlying, to_add, name):
    if hasattr(underlying, name):
        to_add_values = getattr(underlying, name)
        if to_add_values is None:
            setattr(underlying, name, [to_add])
        else:
            to_add_values.append(to_add)
    else:
        setattr(underlying, name, [to_add])


def has_sub(underlying, tys):
    if not hasattr(underlying, DiUtilConstants.subs.name):
        return False
    else:
        return tys in underlying.subs


def get_sub(underlying, matches: typing.Callable) -> typing.Optional:
    if hasattr(underlying, DiUtilConstants.subs.name):
        for s in underlying.subs:
            if matches(s):
                return s


def call_constructable(underlying, self_param, this_param, **kwargs):
    if hasattr(underlying, DiUtilConstants.subs.name):
        constructables, idx = get_constructable(underlying.subs)
        if constructables is not None:
            for constructable in constructables:
                if constructable != this_param:
                    LoggerFacade.debug(f"Calling constructable for {constructable}.")
                    to_include = set(python_util.reflection.reflection_utils
                                     .get_all_fn_param_types(constructable.__init__).keys())
                    to_remove = kwargs.keys() - to_include
                    copied = copy.copy(kwargs)
                    for t in to_remove:
                        del copied[t]
                    constructable.__init__(self_param, **copied)
