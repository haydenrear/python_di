import typing

import injector

from python_di.inject.context_builder.component_scanner import ComponentScanner
from python_di.inject.context_factory.context_factory_editor.base_merge_context_factory import \
    MergedContextFactoriesEditor
from python_di.inject.context_factory.context_factory_executor.context_factories_executor import InjectionContextArgs, \
    InjectMetadataExecutor, AutowireMetadataExecutor, PostConstructMetadataExecutor, PreConstructMetadataExecutor
from python_di.inject.context_factory.context_factory_extractor.context_factory_extract import ContextFactoryExtract
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import BeanComponentFactory


class InjectionContextBuilder:

    @injector.inject
    def __init__(self, context_factories: typing.List[MergedContextFactoriesEditor],
                 context_factory_extract: typing.List[ContextFactoryExtract],
                 context_factories_executor: typing.List[InjectMetadataExecutor],
                 autowire_executor: AutowireMetadataExecutor,
                 post_construct_executor: PostConstructMetadataExecutor,
                 pre_construct: PreConstructMetadataExecutor,
                 component_scanner: ComponentScanner):
        self.component_scanner = component_scanner
        self.pre_construct = pre_construct
        self.autowire_executor = autowire_executor
        self.post_construct_executor = post_construct_executor
        self.context_factories_executor = context_factories_executor
        self.context_factory_extract = context_factory_extract
        self.context_factories = list(sorted(context_factories, key=lambda c: c.ordering()))

    def build_context(self, inject_context_args: InjectionContextArgs):
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        assert isinstance(inject_context_args, InjectionContextInjectorContextArgs)
        self.build_sources(inject_context_args)

        factories_found = self.component_scanner.scan_context_factories(inject_context_args)
        factories_found = self._organize_factories(factories_found)

        self._register_context(factories_found, inject_context_args)
        return factories_found

    def do_lifecycle_hooks(self, factories_found, inject_context_args: InjectionContextArgs):
        self._pre_construct(factories_found, inject_context_args)
        self._autowire_construct(factories_found, inject_context_args)
        self._post_construct(factories_found, inject_context_args)

    def build_sources(self, inject_context_args):
        sources = self.component_scanner.produce_sources(inject_context_args)
        for s in sources:
            if s not in inject_context_args.sources:
                inject_context_args.sources.add(s)

    def _post_construct(self, factories_found, inject_context_args):
        self._construct(factories_found, inject_context_args, self.post_construct_executor)

    def _autowire_construct(self, factories_found, inject_context_args):
        self._construct(factories_found, inject_context_args, self.autowire_executor)

    def _pre_construct(self, factories_found, inject_context_args):
        self._construct(factories_found, inject_context_args, self.pre_construct)

    @staticmethod
    def _construct(factories_found, inject_context_args, executor):
        for f in factories_found:
            for m in f.inject_types:
                if executor.matches(m, inject_context_args):
                    executor.execute(m, inject_context_args)


    def _register_context(self, factories_found, inject_context_args):
        for f in factories_found:
            for m in f.inject_types:
                for c in self.context_factories_executor:
                    if c.matches(m, inject_context_args):
                        c.execute(m, inject_context_args)

    def _organize_factories(self, factories_found):
        for e in self.context_factories:
            factories_found = e.organize_factories(factories_found)
        return factories_found


