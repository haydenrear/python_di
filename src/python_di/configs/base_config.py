import abc

import injector


class DiConfiguration(abc.ABC):
    @abc.abstractmethod
    def lazy(self) -> dict[str, injector.Module]:
        pass

    @abc.abstractmethod
    def initialize(self) -> dict[str, injector.Module]:
        pass
