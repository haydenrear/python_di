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


@inject_context()
def autowired(profile: Optional[typing.Union[Profile, str]] = None, eager_init: bool = False):

    inject = autowired.inject_context()
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
                call_constructable(underlying, self, AutowireProxy, **kwargs)
                super().__init__(*args, **kwargs)
                call_post_construct = []
                for k, v in underlying.__dict__.items():
                    if hasattr(v, DiUtilConstants.wrapped_fn.name):
                        wrapped_fn = getattr(v, DiUtilConstants.wrapped_fn.name)
                        is_wrapped_fn = hasattr(v, '__call__') and hasattr(v, DiUtilConstants.wrapped_fn.name)
                        if is_wrapped_fn and hasattr(wrapped_fn, DiUtilConstants.is_injectable.name):
                            assert hasattr(v, DiUtilConstants.wrapped_fn.name)
                            do_inject, to_construct = self._retrieve_to_construct(v)
                            if do_inject:
                                underlying.__dict__[k](self, **to_construct)
                        elif is_wrapped_fn and hasattr(wrapped_fn, DiUtilConstants.post_construct.name):
                            LoggerFacade.info(f'{cls} has post construct.')
                            call_post_construct.append(v)

                for c in call_post_construct:
                    LoggerFacade.info(f"Calling post construct in {cls} for {AutowireProxy}.")
                    c(self)

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
                self.__dict__[key] = value

            def __getattr__(self, item):
                if item in self.__dict__.keys():
                    return self.__dict__[item]
                else:
                    return None

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
