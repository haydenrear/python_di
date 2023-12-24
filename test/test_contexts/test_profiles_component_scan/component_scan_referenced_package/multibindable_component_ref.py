import abc

from python_di.configs.component import component


class MultibindableInterface(abc.ABC):
    @abc.abstractmethod
    def value(self) -> str:
        pass


@component(bind_to=[MultibindableInterface])
class MultibindableImpl(MultibindableInterface):

    def value(self) -> str:
        return "one"


@component(bind_to=[MultibindableInterface])
class MultibindableImpl2(MultibindableInterface):

    def value(self) -> str:
        return "two"
