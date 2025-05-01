import asyncio
import functools
import threading
import typing
from typing import Optional

import injector
from injector import ScopeDecorator

from python_di.configs.base_config import DiConfiguration
from python_di.configs.constants import LifeCycleHook
from python_di.configs.di_util import get_underlying, get_wrapped_fn, DiUtilConstants, retrieve_wrapped_fn_args, \
    retrieve_fn_ty
from python_di.configs.di_util import has_sub
from python_di.env.profile import Profile
from python_di.inject.context_factory.context_factory_provider.context_factories_provider import \
    InjectableContextFactoryProvider
from python_di.inject.context_factory.context_factory_executor.metadata_factory import LifeCycleMetadataFactory
from python_di.inject.context_factory.context_factory import PostConstructFactory, AutowireFactory, PreConstructFactory
from python_di.inject.context_factory.context_factory_executor.register_factory import retrieve_factory
from python_util.logger.logger import LoggerFacade

registration_lock = threading.RLock()


def autowire(profile: Optional[str] = None,
             injectable_profile: Optional[str] = None,
             priority: Optional[int] = None,
             non_typed_ids: dict[str, typing.Callable[[], typing.Type]] = None,
             scope: Optional[ScopeDecorator] = None):
    if non_typed_ids is not None:
        raise NotImplementedError("Have not implemented non-typed IDs.")

    def wrapped_injectable(fn):
        fn, wrapped = get_wrapped_fn(fn)
        fn_ty = retrieve_fn_ty(fn)

        @functools.wraps(fn)
        def do_inject(*args, **kwargs):
            return fn(*args, **kwargs)

        fn.lifecycle = LifeCycleMetadataFactory(LifeCycleHook.autowire, fn_ty, profile, injectable_profile,
                                                priority, scope)
        fn.wrapped = wrapped
        do_inject.wrapped_fn = fn
        return do_inject

    return wrapped_injectable


def post_construct(fn):
    fn, wrapped = get_wrapped_fn(fn)

    @functools.wraps(fn)
    def do_post_construct(*args, **kwargs):
        LoggerFacade.debug(f"Performing post construct for {fn}.")
        return fn(*args, **kwargs)

    fn.lifecycle = LifeCycleMetadataFactory(LifeCycleHook.post_construct, retrieve_fn_ty(fn))
    do_post_construct.wrapped_fn = fn
    return do_post_construct


def pre_construct(fn):
    fn, wrapped = get_wrapped_fn(fn)

    @functools.wraps(fn)
    def do_pre_construct(*args, **kwargs):
        LoggerFacade.debug(f"Performing pre construct for {fn}.")
        return fn(*args, **kwargs)

    fn.lifecycle = LifeCycleMetadataFactory(LifeCycleHook.pre_construct, retrieve_fn_ty(fn))
    do_pre_construct.wrapped_fn = fn
    return do_pre_construct


def injectable(profile: Optional[typing.Union[Profile, str]] = None,
               scope: Optional[ScopeDecorator] = None):
    LoggerFacade.debug(f"Creating autowire constructor.")

    def create_constructor(cls_value):
        underlying = get_underlying(cls_value)
        LoggerFacade.debug(f"Creating autowire constructor for {underlying}.")

        if has_sub(underlying, DiConfiguration):
            raise ValueError(f"{cls_value} was annotated with both autowire and configuration. Can only be one or the "
                             f"other.")

        class InjectableProxy(InjectableContextFactoryProvider):

            def __init__(self, *args, **kwargs):
                LoggerFacade.debug(f"Initializing autowire proxy for {underlying}.")
                super().__init__(*args, **kwargs)
                self.did_register = asyncio.Event()
                self._pre_construct_factory, self._autowire_factory, self._post_construct_factory \
                    = self._iterate_constructables()
                out_factories = []
                out_factories.extend(self._post_construct_factory)
                out_factories.extend(self._autowire_factory)
                out_factories.extend(self._pre_construct_factory)
                self._context_factory = out_factories

            @injector.synchronized(registration_lock)
            def did_already_register_factories(self):
                if self.did_register.is_set():
                    return True
                else:
                    self.did_register.set()
                    return False

            @property
            def context_factory(self) -> list[typing.Union[PostConstructFactory, AutowireFactory, PreConstructFactory]]:
                if not self.did_register.is_set():
                    if not self.did_already_register_factories():
                        return self._context_factory
                LoggerFacade.error("Attempted to register factories for injectable with hooks multiple times!")
                return self._context_factory

            @property
            def post_construct_factory(self) -> list[PostConstructFactory]:
                return self._post_construct_factory

            @property
            def autowire_factory(self) -> list[AutowireFactory]:
                return self._autowire_factory

            @property
            def pre_construct_factory(self) -> list[PreConstructFactory]:
                return self._pre_construct_factory

            @classmethod
            def _iterate_constructables(cls) -> (list[PreConstructFactory],
                                                 list[AutowireFactory],
                                                 list[PostConstructFactory]):
                """
                Iterate over the class members (of the underlying class) and add all @injectable and @post_construct
                to lists, and then return them.
                :return:
                """
                call_post_construct = []
                call_pre_construct = []
                call_autowire = []
                for k, v in underlying.__dict__.items():
                    if (hasattr(v, DiUtilConstants.wrapped_fn.name)
                            and hasattr(v.wrapped_fn, DiUtilConstants.lifecycle.name)):
                        wrapped_fn = getattr(v, DiUtilConstants.wrapped_fn.name)
                        is_wrapped_fn = hasattr(v, '__call__') and hasattr(v, DiUtilConstants.wrapped_fn.name)
                        # if profile/scope not provided at annotation level, inherit profile and scope from the
                        # class for which the function is defined.
                        lifecycle = cls._update_lifecycle_metadata(v.wrapped_fn)
                        if is_wrapped_fn:
                            cls._register_lifecycle_hooks(cls_value, call_autowire, call_post_construct,
                                                          call_pre_construct, lifecycle, wrapped_fn)
                        else:
                            LoggerFacade.error(f"Wrapped fn {k} for {cls.__name__} failed to be callable.")
                return call_pre_construct, call_autowire, call_post_construct

            @staticmethod
            def _update_lifecycle_metadata(v):
                lifecycle: LifeCycleMetadataFactory = v.lifecycle
                if lifecycle.profile is None and profile is not None:
                    lifecycle.profile = profile
                if lifecycle.scope_decorator is None and scope is not None:
                    lifecycle.scope_decorator = scope
                return lifecycle

            @classmethod
            def _register_lifecycle_hooks(cls, cls_value, call_autowire, call_post_construct, call_pre_construct,
                                          lifecycle, wrapped_fn):
                if lifecycle.life_cycle_hook == LifeCycleHook.autowire:
                    cls.create_add_i_factory(cls_value, call_autowire, lifecycle, wrapped_fn,
                                             AutowireFactory)
                elif lifecycle.life_cycle_hook == LifeCycleHook.pre_construct:
                    cls.create_add_i_factory(cls_value, call_pre_construct, lifecycle, wrapped_fn,
                                             PreConstructFactory)
                elif lifecycle.life_cycle_hook == LifeCycleHook.post_construct:
                    cls.create_add_i_factory(cls_value, call_post_construct, lifecycle, wrapped_fn,
                                             PostConstructFactory)
                else:
                    LoggerFacade.error(
                        f"Received unknown lifecycle hook: {lifecycle.life_cycle_hook.name}.")

            @classmethod
            def create_add_i_factory(cls, cls_value, call_pre_construct, lifecycle, wrapped_fn, factory_ty):
                fn_arg_tys = retrieve_wrapped_fn_args(wrapped_fn)
                pre_construct_factory = factory_ty(cls_value, underlying, wrapped_fn, fn_arg_tys, lifecycle)
                pre_construct_factory.args = lambda: cls._retrieve_args(pre_construct_factory, lifecycle)
                call_pre_construct.append(pre_construct_factory)

            @classmethod
            def _retrieve_args(cls, _pre_construct_factory, _lifecycle):
                did_inject, values = retrieve_factory(_pre_construct_factory, _lifecycle)
                return values

        cls_value.proxied = underlying
        cls_value.context_factory_provider = InjectableProxy()
        cls_value.injectable_context_factory = True
        return cls_value

    return create_constructor
