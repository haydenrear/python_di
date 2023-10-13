import abc
from typing import Generic, TypeVar


class Delegatable(abc.ABC):
    @abc.abstractmethod
    def do_delegation(self, *args, **kwargs):
        pass


DelegatorTypeT = TypeVar("DelegatorTypeT", covariant=True, bound=Delegatable)


class InjectableDelegations(Generic[DelegatorTypeT], abc.ABC):

    def __init__(self, delegators: list[DelegatorTypeT]):
        self.delegators = delegators

    def do_delegation_action(self, *args, **kwargs):
        for delegate in self.delegators:
            delegate: DelegatorTypeT = delegate
            delegate.do_delegation(*args, **kwargs)
