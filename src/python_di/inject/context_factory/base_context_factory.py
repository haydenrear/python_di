import abc
import typing

from python_di.inject.context_factory.type_metadata.base_ty_metadata import InjectTypeMetadata


class CallableFactory(abc.ABC):
    @property
    @abc.abstractmethod
    def to_call(self) -> typing.Callable:
        pass


class ContextFactory(abc.ABC):

    @property
    @abc.abstractmethod
    def inject_types(self) -> list[InjectTypeMetadata]:
        pass
