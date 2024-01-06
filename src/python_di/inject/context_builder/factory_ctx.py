import typing

import injector
from injector import Binder

from python_di.inject.binder_utils import bind_multi_bind
from python_di.inject.context_builder.component_scanner import ComponentScanner
from python_di.inject.context_builder.injection_context_builder import InjectionContextBuilder
from python_di.inject.context_factory.context_factory_editor.base_merge_context_factory import \
    MergedContextFactoriesEditor
from python_di.inject.context_factory.context_factory_editor.lifecycle_context_factory import \
    LifecycleContextFactoriesEditor
from python_di.inject.context_factory.context_factory_editor.merge_profile_factories_editor import \
    MergedProfileFactoriesEditor
from python_di.inject.context_factory.context_factory_editor.merged_context_factories import \
    MergedConfigurationContextFactoriesEditor, MergedComponentContextFactoriesEditor, \
    MergedInjectionContextFactoriesEditor, ConfigurationPropertiesContextFactoriesEditor, \
    PrototypeContextFactoriesEditor
from python_di.inject.context_factory.context_factory_editor.multibind_context_factory import \
    MultibindContextFactoryEditor
from python_di.inject.context_factory.context_factory_executor.context_factories_executor import InjectMetadataExecutor, \
    AutowireMetadataExecutor, PreConstructMetadataExecutor, PostConstructMetadataExecutor, \
    RegisterFactoryMetadataExecutor
from python_di.inject.context_factory.context_factory_extractor.context_factory_extract import \
    ConfigurationContextFactoryExtract, ComponentContextFactoryExtract, ContextFactoryExtract, \
    ConfigurationPropertiesFactoryExtract, PrototypeFactoryExtract, InjectableFactoryExtract


class FactoryCtx(injector.Module):

    def configure(self, binder: Binder) -> None:
        bind_multi_bind(self._factories_editors(), binder, typing.List[MergedContextFactoriesEditor])
        bind_multi_bind(self._context_factory_extractors(), binder, typing.List[ContextFactoryExtract])
        bind_multi_bind(self._context_exexecutors(), binder, typing.List[InjectMetadataExecutor])

        binder.bind(AutowireMetadataExecutor, AutowireMetadataExecutor, scope=injector.singleton)
        binder.bind(PreConstructMetadataExecutor, PreConstructMetadataExecutor, scope=injector.singleton)
        binder.bind(PostConstructMetadataExecutor, PostConstructMetadataExecutor, scope=injector.singleton)

        binder.bind(InjectionContextBuilder, InjectionContextBuilder, scope=injector.singleton)
        binder.bind(ComponentScanner, ComponentScanner, scope=injector.singleton)

    def _factories_editors(self):
        return [ConfigurationPropertiesContextFactoriesEditor, MergedProfileFactoriesEditor,
                MergedInjectionContextFactoriesEditor, MergedComponentContextFactoriesEditor,
                MergedConfigurationContextFactoriesEditor, PrototypeContextFactoriesEditor,
                MultibindContextFactoryEditor,
                # LifecycleContextFactoriesEditor
                ]

    def _context_factory_extractors(self):
        return [
            ConfigurationPropertiesFactoryExtract, ComponentContextFactoryExtract, ConfigurationContextFactoryExtract,
            PrototypeFactoryExtract, InjectableFactoryExtract
        ]

    def _context_exexecutors(self):
        return [RegisterFactoryMetadataExecutor]
