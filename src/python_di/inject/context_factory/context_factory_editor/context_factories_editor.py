import abc

from python_di.inject.context_factory.base_context_factory import ContextFactory


class ContextFactoriesEditor(abc.ABC):
    """
    Answers the question of how to enforce an order of the injection factories, as the ordering that the context
    is passed into container creation will determine how the beans are wired. So it will iterate through all
    context factories and edit their metadata, re-order them, add them, merge them, remove them, etc, and then
    return them to be executed in the container.
    """

    @abc.abstractmethod
    def organize_factories(self, factories: list[ContextFactory]) -> list[ContextFactory]:
        pass

    def ordering(self) -> int:
        return 0


