import abc
import dataclasses
import typing

from python_di.env.profile import Profile
from python_di.env.profile_config_props import ProfileProperties
from python_di.inject.context_factory.context_factory_editor.context_factories_editor import ContextFactoriesEditor
from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


@dataclasses.dataclass(init=True)
class MergedContextFactory(ContextFactory, abc.ABC):
    profile: Profile
    bean_metadata: list[InjectTypeMetadata]

    @property
    def inject_types(self) -> list[InjectTypeMetadata]:
        return self.bean_metadata


@dataclasses.dataclass(init=True)
class MergedContextFactoryFactory:
    bean_metadata: dict[Profile, list[InjectTypeMetadata]] = None

    @autowire_fn()
    def register_bean_metadata(self, bean_component_factory: InjectTypeMetadata,
                               profiles: ProfileProperties):
        if self.bean_metadata is None:
            self.bean_metadata = {}

        for factory in bean_component_factory.split_for_profiles():
            self._add_profile_to_bean_metadata(factory, profiles)

    def _add_profile_to_bean_metadata(self, bean_component_factory, profiles):
        profile_retrieved = profiles.create_get_profile(bean_component_factory.profile if bean_component_factory.profile
                                                        is not None else profiles.default_profile.profile_name,
                                                        bean_component_factory.priority if bean_component_factory.priority
                                                        is not None else profiles.default_profile.priority)
        self._add_to_bean_metadata(bean_component_factory, profile_retrieved)

    def _add_to_bean_metadata(self, bean_component_factory, profile_retrieved):
        assert bean_component_factory.priority is None or profile_retrieved.priority == bean_component_factory.priority, \
            (f"Profile priority {bean_component_factory.priority} did not match provided in properties: "
             f"{profile_retrieved.priority}")
        if profile_retrieved in self.bean_metadata.keys():
            self.bean_metadata[profile_retrieved].append(bean_component_factory)
        else:
            self.bean_metadata[profile_retrieved] = [bean_component_factory]

    def create_factories(self, context_factory: typing.Type) -> list[MergedContextFactory]:
        if self.bean_metadata is None:
            return []
        return [context_factory(k, v)
                for (k, v) in sorted(self.bean_metadata.items(), key=lambda kv: kv[0])]


class MergedContextFactoriesEditor(ContextFactoriesEditor, abc.ABC):
    """
    Merge together by factory by profile first in case something needs to be updated across factory.
    """
    @property
    @abc.abstractmethod
    def merged_context_factory(self) -> typing.Type:
        pass

    @abc.abstractmethod
    def ordering(self) -> int:
        pass

    @abc.abstractmethod
    def is_factory_ty(self, f: ContextFactory):
        pass

    def organize_factories(self, factories: list[ContextFactory]) -> list[ContextFactory]:
        config_factories = MergedContextFactoryFactory()
        to_remove = []
        for i, f in enumerate(factories):
            if self.is_factory_ty(f):
                if f.inject_types is not None:
                    for inject_ty in filter(lambda inj: inj, f.inject_types):
                        config_factories.register_bean_metadata(inject_ty)
                to_remove.append(f)

        for t in to_remove:
            factories.remove(t)

        factories.extend(config_factories.create_factories(self.merged_context_factory))

        return factories
