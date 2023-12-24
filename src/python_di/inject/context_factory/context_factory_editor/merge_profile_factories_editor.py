import abc
import dataclasses

from python_di.env.profile import Profile
from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata
from python_di.inject.context_factory.context_factory_editor.base_merge_context_factory import MergedContextFactory
from python_di.inject.context_factory.context_factory_editor.context_factories_editor import ContextFactoriesEditor


@dataclasses.dataclass(init=True)
class MergedProfileFactory(ContextFactory, abc.ABC):
    profile: Profile
    bean_metadata: list[InjectTypeMetadata]

    @property
    def inject_types(self) -> list[InjectTypeMetadata]:
        return self.bean_metadata


@dataclasses.dataclass(init=True)
class MergedProfileFactoryFactory:
    bean_metadata: dict[Profile, list[InjectTypeMetadata]] = None

    def register_factory(self, merged_factory: MergedContextFactory):
        profile_retrieved = merged_factory.profile
        if profile_retrieved in self.bean_metadata.keys():
            self.bean_metadata[profile_retrieved].extend(merged_factory.bean_metadata)
        else:
            self.bean_metadata[profile_retrieved] = merged_factory.bean_metadata

    def create_factories(self) -> list[MergedProfileFactory]:
        return [MergedProfileFactory(k, v)
                for (k, v) in sorted(self.bean_metadata.items(), key=lambda kv: kv[0])]


class MergedProfileFactoriesEditor(ContextFactoriesEditor):
    """
    Merge together by factory by profile first in case something needs to be updated across factory.
    """

    def ordering(self) -> int:
        return -5

    def organize_factories(self, factories: list[ContextFactory]) -> list[ContextFactory]:
        config_factories = MergedProfileFactoryFactory({})
        i = -1
        for i, f in enumerate(factories):
            assert isinstance(f, MergedContextFactory), \
                f"All context factories should be {MergedContextFactory.__name__} but was {type(f).__name__}."
            config_factories.register_factory(f)

        if i != -1:
            assert i == len(factories) - 1, f"Factories was wrong size: {i} instead of {len(factories)}."

        factories.clear()
        factories.extend(config_factories.create_factories())

        return factories
