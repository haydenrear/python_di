from typing import Optional

import injector

from python_di.configs.constants import LifeCycleHook, FnTy


class MetadataFactory:
    def __init__(self,
                 injectable_profile: Optional[str] = None,
                 injectable_priority: Optional[int] = None,
                 scope_decorator: Optional[injector.ScopeDecorator] = None):
        self.scope_decorator = scope_decorator
        self.injectable_priority = injectable_priority
        self.injectable_profile = injectable_profile


class LifeCycleMetadataFactory(MetadataFactory):
    def __init__(self,
                 life_cycle_hook: LifeCycleHook,
                 life_cycle_type: FnTy,
                 injectable_profile: Optional[str] = None,
                 injectable_priority: Optional[int] = None,
                 scope_decorator: Optional[injector.ScopeDecorator] = None):
        MetadataFactory.__init__(self, injectable_profile, injectable_priority, scope_decorator)
        self.life_cycle_type = life_cycle_type
        self.life_cycle_hook = life_cycle_hook
