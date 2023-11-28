import typing

from python_util.reflection.reflection_utils import is_type_instance_of

T = typing.TypeVar("T")


def is_multibindable(type_to_check: typing.Type[T]):
    return (is_type_instance_of(type_to_check, dict)
            or is_type_instance_of(type_to_check, set)
            or is_type_instance_of(type_to_check, list))
