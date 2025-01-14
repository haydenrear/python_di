import abc

from reflection_tests.reflection_test_fixtures_import import FoundationTokenizer


class TokenizerId:
    pass


class Config:
    pass


class ConfigFactory(Config):
    pass


class FoundationTokenizerImport(FoundationTokenizer):

    @property
    def vocab_size(self) -> int:
        pass

    @property
    def eos_token_id(self) -> int:
        pass


class FoundationTokenizerConfig(Config, abc.ABC):
    pass


class HuggingfaceTokenizerConfig(FoundationTokenizerConfig):
    pass


class HuggingfaceFoundationTokenizerConfig(FoundationTokenizerConfig):
    pass


class FoundationTokenizerFactory(ConfigFactory, abc.ABC):
    pass


class HuggingFaceTokenizerConfigFactory(FoundationTokenizerFactory):
    pass
