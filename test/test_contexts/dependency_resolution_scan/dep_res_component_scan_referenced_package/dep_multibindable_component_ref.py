import abc

from python_di.configs.component import component


class DepMultibindableInterface(abc.ABC):
    @abc.abstractmethod
    def value(self) -> str:
        pass


@component(bind_to=[DepMultibindableInterface])
class DepMultibindableImpl(DepMultibindableInterface):

    def value(self) -> str:
        return "one"


@component(bind_to=[DepMultibindableInterface])
class DepMultibindableImpl2(DepMultibindableInterface):

    def value(self) -> str:
        return "two"
