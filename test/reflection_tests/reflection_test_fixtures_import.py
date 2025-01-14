import abc

import torch


class FoundationTokenizer(torch.nn.Module, abc.ABC):
    @property
    @abc.abstractmethod
    def vocab_size(self) -> int:
        pass

    @vocab_size.setter
    @abc.abstractmethod
    def vocab_size(self, vocab_size: int):
        pass

    @property
    @abc.abstractmethod
    def eos_token_id(self) -> int:
        pass

    @eos_token_id.setter
    @abc.abstractmethod
    def eos_token_id(self, eos_token_id: int):
        pass
