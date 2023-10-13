import injector as injector
from injector import Binder

from drools_py.configs.config_adapters import LinearLayerConfigAdapterProv, MultiHeadAttentionConfigAdapterProv, \
    TchConfigAdapterProvider, TchConfigAdapters


class TorchModuleIntrospector(injector.Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(TchConfigAdapterProvider, TchConfigAdapters([
            MultiHeadAttentionConfigAdapterProv(),
            LinearLayerConfigAdapterProv()
        ]))