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
    is_injectable = enum.auto()
    class_configs = enum.auto()
    post_construct = enum.auto()
    type_id = enum.auto()
    subs = enum.auto()
    fallback = enum.auto()
