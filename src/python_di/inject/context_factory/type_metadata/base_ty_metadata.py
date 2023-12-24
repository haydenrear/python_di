import abc
import typing

import injector

T = typing.TypeVar("T")

class HasFnArgs(abc.ABC):
    @property
    @abc.abstractmethod
    def fn_args(self) -> dict[str, type]:
        pass


class InjectTypeMetadata(HasFnArgs, abc.ABC):

    def __init__(self,
                 ty_to_inject: typing.Type[T],
                 underlying: typing.Type,
                 profile: typing.Union[str, list[str]],
                 priority: int,
                 scope: injector.ScopeDecorator,
                 dependencies: dict[str, ...],
                 bindings: list[typing.Type]):
        self.bindings = bindings
        self.dependencies = dependencies
        self.scope = scope
        self.priority = priority
        self.profile = profile
        self.underlying = underlying
        self.ty_to_inject = ty_to_inject

    @property
    def fn_args(self) -> dict[str, type]:
        return self.dependencies

    def split_for_profiles(self) -> list:
        if isinstance(self.profile, str | None):
            return [self]
        else:
            return [
                InjectTypeMetadata(self.ty_to_inject, self.underlying, p, self.priority, self.scope,
                                   self.dependencies, self.bindings)
                for p in self.profile
            ]
