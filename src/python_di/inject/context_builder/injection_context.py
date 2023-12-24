import dataclasses
import threading
from typing import Optional

import injector as injector
from injector import Binder

from python_di.inject.context_builder.injection_context_builder import InjectionContextBuilder
from python_di.inject.context_factory.context_factory_executor.context_factories_executor import InjectionContextArgs
from python_di.inject.context_builder.inject_ctx import inject_context
from python_di.inject.injector_provider import InjectionContextInjector
from python_di.inject.profile_composite_injector.composite_injector import CompositeInjector

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
    ctx: InjectionContextInjector = None

    @injector.synchronized(injector_lock)
    def initialize_env(self):
        if self.ctx is None:
            self.ctx = CompositeInjector([InjectorInjectionModule]).get(InjectionContextInjector)
            inject_context(self.ctx)
        if not self.ctx.did_initialize_env.is_set() is None:
            self.ctx.initialize_env_profiles()
            assert self.ctx.did_initialize_env.is_set(), "Was not set"

        return self.ctx

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

        context_builder.build_context(InjectionContextInjectorContextArgs(self.ctx, parent_sources, source_directory))

        for b in self.ctx.injectors_dictionary.injectors.values():
            b.collapse_injectors()
