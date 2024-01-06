import dataclasses
import typing

from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.context_factory import LifecycleFactory
from python_di.inject.context_factory.context_factory_editor.context_factories_editor import ContextFactoriesEditor
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import MultibindTypeMetadata


class LifecycleContextFactoriesEditor(ContextFactoriesEditor):
    """
    Answers the question of how to enforce an order of the injection factories, as the ordering that the context
    is passed into container creation will determine how the beans are wired. So it will iterate through all
    context factories and edit their metadata, re-order them, add them, merge them, remove them, etc, and then
    return them to be executed in the container.
    """

    def organize_factories(self, factories: list[ContextFactory]) -> list[ContextFactory]:
        new_inject_tys: list[LifecycleFactory] = []
        for inject_ty_metadata in [i for f in factories for i in f.inject_types]:
            if self._has_lifecycle_hooks(inject_ty_metadata):
                next_multibind = inject_ty_metadata.ty_to_inject.context_factory_provider
                new_inject_tys.extend(next_multibind.context_factory)

        factories.extend(new_inject_tys)
        return factories

    @staticmethod
    def _has_lifecycle_hooks(inject_ty_metadata):
        return (hasattr(inject_ty_metadata.ty_to_inject, 'injectable_context_factory')
                and not inject_ty_metadata.ty_to_inject.context_factory_provider.did_register.is_set())

    def ordering(self) -> int:
        """
        Before merging by profiles.
        :return:
        """
        return -5


