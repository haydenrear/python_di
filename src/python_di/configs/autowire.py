import abc
import typing
from typing import Optional

import injector

from python_di.configs.base_config import DiConfiguration
from python_di.configs.constructable import ConstructableMarker
from python_di.configs.di_util import add_subs, \
    has_sub, call_constructable
from python_di.configs.di_util import get_underlying, get_wrapped_fn, retrieve_factory, DiUtilConstants
from python_di.env.profile import Profile
from python_di.inject.inject_context import inject_context
from python_util.delegate.delegates import PythonDelegate
from python_util.logger.logger import LoggerFacade


def injectable(profile: Optional[str] = None,
               non_typed_ids: dict[str, typing.Callable[[], typing.Type]] = None):
    if non_typed_ids is not None:
        raise NotImplementedError("Have not implemented non-typed IDs.")

    def wrapped_injectable(fn):
        fn, wrapped = get_wrapped_fn(fn)

        def do_inject(*args, **kwargs):
            return fn(*args, **kwargs)

        fn.is_injectable = True
        fn.injectable_profile = profile
        fn.wrapped = wrapped
        do_inject.wrapped_fn = fn
        return do_inject

    return wrapped_injectable


def post_construct(fn):
    fn, wrapped = get_wrapped_fn(fn)

    def do_post_construct(*args, **kwargs):
        LoggerFacade.debug(f"Performing post construct for {fn}.")
        return fn(*args, **kwargs)

    fn.post_construct = True
    do_post_construct.wrapped_fn = fn
    return do_post_construct


class Autowired:
    pass


def autowired(profile: Optional[typing.Union[Profile, str]] = None):
    LoggerFacade.debug(f"Creating autowire constructor.")

    def create_constructor(cls):
        underlying = get_underlying(cls)
        LoggerFacade.debug(f"Creating autowire constructor for {underlying}.")

        if has_sub(underlying, DiConfiguration):
            raise ValueError(f"{cls} was annotated with both autowire and configuration. Can only be one or the "
                             f"other.")

        class AutowireProxy(cls):
            def __init__(self, *args, **kwargs):
                LoggerFacade.debug(f"Initializing autowire proxy for {underlying}.")
                super().__init__(*args, **kwargs)
                call_constructable(cls, underlying, self, AutowireProxy, **kwargs)
                call_post_construct, to_call = self._iterate_constructables()
                self._do_construct_autowire(to_call)
                self._call_post_constructs(call_post_construct)

            @staticmethod
            def _iterate_constructables():
                """
                Iterate over the class members (of the underlying class) and add all @injectable and @post_construct
                to lists, and then return them.
                :return:
                """
                call_post_construct = []
                to_call = []
                for k, v in underlying.__dict__.items():
                    if hasattr(v, DiUtilConstants.wrapped_fn.name):
                        wrapped_fn = getattr(v, DiUtilConstants.wrapped_fn.name)
                        is_wrapped_fn = hasattr(v, '__call__') and hasattr(v, DiUtilConstants.wrapped_fn.name)
                        if is_wrapped_fn and hasattr(wrapped_fn, DiUtilConstants.is_injectable.name):
                            assert hasattr(v, DiUtilConstants.wrapped_fn.name)
                            to_call.append((k, v))
                        elif is_wrapped_fn and hasattr(wrapped_fn, DiUtilConstants.post_construct.name):
                            LoggerFacade.info(f'{cls} has post construct.')
                            call_post_construct.append(v)
                return call_post_construct, to_call

            def _call_post_constructs(self, call_post_construct):
                """
                Call @post_construct
                :param call_post_construct: list of functions annotated with @post_constructs, which have no arguments.
                :return:
                """
                for c in call_post_construct:
                    LoggerFacade.info(f"Calling post construct in {cls} for {AutowireProxy}.")
                    c(self)

            def _do_construct_autowire(self, to_call):
                """
                Autowire-ables are annotated with @injectable - they are in the above list, so retrieve the args
                and then call them.
                :param to_call:
                :return:
                """
                for (k, v) in to_call:
                    do_inject, to_construct = self._retrieve_to_construct(v)
                    if do_inject:
                        LoggerFacade.info(f"Calling inject on {v} for {k} and "
                                          f"{to_construct}.")
                        v(self, **to_construct)

            @staticmethod
            def _retrieve_to_construct(v):
                v = v.wrapped_fn
                if hasattr(v, DiUtilConstants.injectable_profile.name) and v.injectable_profile is not None:
                    LoggerFacade.debug(f"Creating factory with injectable profile {v.injectable_profile}.")
                    do_inject, to_construct = retrieve_factory(v, v.injectable_profile)
                else:
                    do_inject, to_construct = retrieve_factory(v, profile)
                return do_inject, to_construct

            def __setattr__(self, key, value):
                try:
                    super().__setattr__(key, value)
                except:
                    self.__dict__[key] = value

            def __getattr__(self, item):
                found = self._try_get_attr_super(item)
                if found is not None:
                    return found
                else:
                    found = self._search_get_attr_super(item)
                    if found is not None:
                        return found
                    else:
                        raise AttributeError(f"Did not contain {item}!")

            def _try_get_attr_super(self, item):
                try:
                    return super().__getattr__(item)
                except:
                    pass

            def _search_get_attr_super(self, item):
                if hasattr(self.proxied, item):
                    return getattr(self.proxied, item)
                else:
                    super_class = super()
                    if hasattr(super_class, item):
                        return super_class.__getattr__(item)
                    elif hasattr(cls, item):
                        return getattr(cls, item)
                    else:
                        for b in type(self).__mro__:
                            if hasattr(b, item):
                                return getattr(b, item)

        AutowireProxy.proxied = underlying
        add_subs(underlying, [{ConstructableMarker: AutowireProxy}])
        return AutowireProxy

    return create_constructor


@inject_context()
def config_option(bind_to: list[type] = None, profile: Optional[str] = None):
    inject = config_option.inject_context()

    def class_decorator_inner(cls):
        binding = bind_to if bind_to is not None else [cls]
        if cls not in binding:
            binding.append(cls)
        inject.register_component_value(cls, getattr(cls, f"build_{profile}_config")(),
                                        injector.singleton, profile)
        return cls

    return class_decorator_inner
