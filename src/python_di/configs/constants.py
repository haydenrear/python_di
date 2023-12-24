import enum


class DiUtilConstants(enum.Enum):
    profile = enum.auto()
    inject_context = enum.auto()
    wrapped_fn = enum.auto()
    injectable_profile = enum.auto()
    prefix_name = enum.auto()
    proxied = enum.auto()
    wrapped = enum.auto()
    is_bean = enum.auto()
    is_lazy = enum.auto()
    class_configs = enum.auto()
    post_construct = enum.auto()
    type_id = enum.auto()
    subs = enum.auto()
    fallback = enum.auto()
    lifecycle = enum.auto()
    ctx = enum.auto()


class ContextFactoryIdentifiers(enum.Enum):
    context_factory = enum.auto()
    configuration_context_factory = enum.auto()
    component_context_factory = enum.auto()
    injectable_context_factory = enum.auto()
    config_properties_context_factory = enum.auto()
    prototype_bean_factory_ty = enum.auto()


class LifeCycleHook(enum.Enum):
    pre_construct = enum.auto()
    post_construct = enum.auto()
    autowire = enum.auto()


class FnTy(enum.Enum):
    class_method = enum.auto()
    self_method = enum.auto()
    static_method = enum.auto()
    init_method = enum.auto()


class ContextDecorators(enum.Enum):
    configuration = enum.auto()
    component = enum.auto()
    enable_configuration_properties = enum.auto()
    injectable = enum.auto()
    prototype_scope_bean = enum.auto()

    @classmethod
    def context_ids(cls) -> list[str]:
        return [i for i in ContextDecorators._member_map_.keys()]