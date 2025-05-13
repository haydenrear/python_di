import dataclasses
import threading
import typing
from typing import Optional

import injector as injector
from injector import Binder

from python_di.inject.context_builder.injection_context_builder import InjectionContextBuilder
from python_di.inject.context_factory.context_factory_executor.context_factories_executor import InjectionContextArgs
from python_di.inject.context_builder.inject_ctx import inject_context
from python_di.inject.injector_provider import InjectionContextInjector
from python_di.inject.profile_composite_injector.composite_injector import CompositeInjector
from python_di.inject.profile_composite_injector.scopes.composite_scope import CompositeScope

injector_lock = threading.RLock()


class InjectorInjectionModule(injector.Module):
    def configure(self, binder: Binder):
        binder.bind(InjectionContextInjector, to=InjectionContextInjector, scope=injector.singleton)

@dataclasses.dataclass(init=True)
class InjectionContextInjectorContextArgs(InjectionContextArgs):
    injection_context_injector: InjectionContextInjector
    sources: set[str]
    starting: str


class InjectionContext:
    ctx: typing.Optional[InjectionContextInjector] = None

    @classmethod
    @injector.synchronized(injector_lock)
    def reset(cls):
        cls.ctx = None
        inject_context.ctx = None

    @injector.synchronized(injector_lock)
    def initialize_env(self, profile_name_override = None, env_source = None):
        if self.ctx is None:
            self.ctx = CompositeInjector([InjectorInjectionModule]).get(InjectionContextInjector)
            inject_context(self.ctx)
        if not self.ctx.did_initialize_env.is_set() is None:
            self.ctx.initialize_env_profiles(profile_name_override, env_source)
            assert self.ctx.did_initialize_env.is_set(), "Was not set"

        return self.ctx

    @injector.synchronized(injector_lock)
    def merge_context(self,
                      parent_sources: set[str],
                      source_directory: Optional[str] = None):
        """
        TODO: parse the context lazily instead of eagerly, merge together scopes
        :param parent_sources:
        :param source_directory:
        :return:
        """
        raise ValueError("Is not implemented.")

    @injector.synchronized(injector_lock)
    def build_context(self,
                      parent_sources: set[str],
                      source_directory: Optional[str] = None):
        """
        Build the context using the files referenced in parent_sources to scan the context.
        :param source_directory:
        :param parent_sources:
        :return:
        """
        if source_directory is None:
            source_directory = next(iter(parent_sources))

        context_builder: InjectionContextBuilder \
            = self.ctx.get_interface(InjectionContextBuilder, scope=injector.singleton)

        ctx_args = InjectionContextInjectorContextArgs(self.ctx, parent_sources, source_directory)
        factories = context_builder.build_context(ctx_args)

        composite_scope = None
        for b in self.ctx.injectors_dictionary.injectors.values():
            b.collapse_injectors()
            if composite_scope is not None:
                assert composite_scope == b.composite_scope
            else:
                composite_scope = b.composite_scope

        self.organize_composite_scope(composite_scope)

        context_builder.do_lifecycle_hooks(factories, ctx_args)

    @staticmethod
    def organize_composite_scope(composite_scope: CompositeScope):
        #  TODO:
        # composite scope should register the highest priority profile bean as the singleton bean, if there does not
        # exist a singleton bean for that bean.
        assert composite_scope is not None
        composite_scope.injector.mark_immutable()
        return composite_scope