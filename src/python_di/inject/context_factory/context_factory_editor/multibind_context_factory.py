import dataclasses
import typing

from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.context_factory_editor.context_factories_editor import ContextFactoriesEditor
from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata
from python_di.inject.context_factory.type_metadata.inject_ty_metadata import MultibindTypeMetadata


@dataclasses.dataclass(init=True)
class MultibindContextFactory(ContextFactory):
    _inject_types: list[MultibindTypeMetadata]


    @property
    def inject_types(self) -> list[MultibindTypeMetadata]:
        return self._inject_types


class MultibindContextFactoryEditor(ContextFactoriesEditor):
    """
    Answers the question of how to enforce an order of the injection factories, as the ordering that the context
    is passed into container creation will determine how the beans are wired. So it will iterate through all
    context factories and edit their metadata, re-order them, add them, merge them, remove them, etc, and then
    return them to be executed in the container.
    """

    def organize_factories(self, factories: list[ContextFactory]) -> list[ContextFactory]:
        bound_values: dict[str, dict[type, list[InjectTypeMetadata]]] = {}
        for inject_ty_metadata in [i for f in factories for i in f.inject_types]:
            if self._is_multibindable(inject_ty_metadata):
                if isinstance(inject_ty_metadata.profile, str):
                    self._add_ty_metadata_to_profile(bound_values, inject_ty_metadata, inject_ty_metadata.profile)
                elif isinstance(inject_ty_metadata.profile, list):
                    for profile in inject_ty_metadata.profile:
                        self._add_ty_metadata_to_profile(bound_values, inject_ty_metadata, profile)
                else:
                    from python_di.env.base_env_properties import DEFAULT_PROFILE
                    self._add_ty_metadata_to_profile(bound_values, inject_ty_metadata, DEFAULT_PROFILE)

        new_inject_tys: list[MultibindContextFactory] = []


        for profile, bound_dict in bound_values.items():
            v = []
            for bound_id, bound_value in bound_dict.items():
                b: InjectTypeMetadata = next(iter(bound_value))
                s = b.scope
                has_same_scope = all([s == b_item.scope or b_item.scope or s is None is None for b_item in bound_value])
                assert has_same_scope
                next_multibind = MultibindTypeMetadata(typing.List[bound_id], profile, s, bound_value)
                v.append(next_multibind)
            new_inject_tys.append(MultibindContextFactory(v))

        factories.extend(new_inject_tys)
        return factories

    def _is_multibindable(self, inject_ty_metadata):
        return inject_ty_metadata.bindings is not None and len(inject_ty_metadata.bindings) != 0 \
            and not (len(inject_ty_metadata.bindings) == 1
                     and inject_ty_metadata.bindings[0] == inject_ty_metadata.ty_to_inject)

    def _add_ty_metadata_to_profile(self, bound_values, inject_ty_metadata, profile):
        if profile not in bound_values.keys():
            bound_values[profile] = {}
        for b in inject_ty_metadata.bindings:
            if b not in bound_values[profile].keys():
                bound_values[profile][b] = [inject_ty_metadata]
            else:
                bound_values[profile][b].append(inject_ty_metadata)

    def ordering(self) -> int:
        """
        Before merging by profiles.
        :return:
        """
        return -4


