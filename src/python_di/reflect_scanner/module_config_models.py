import abc
from typing import Optional, Generic, TypeVar


class Reflectable(abc.ABC):
    @abc.abstractmethod
    def to_dict(self) -> dict:
        pass


class ConstructorArg:
    def __init__(self,
                 class_def,
                 arg_name: str,
                 value: Optional = None):
        self.value = value
        self.name = arg_name
        self.class_def = class_def

    def to_dict(self) -> dict:
        return {
            "class_def": self.class_def.to_self_dictionary() if self.class_def else None,
            "arg_name": self.name
        }


class ClassDef:
    def __init__(self,
                 name: str,
                 key: Optional = None,
                 value: Optional = None,
                 lst: Optional = None,
                 opt: Optional = None,
                 gen: Optional = None,
                 constructor_args: list[ConstructorArg] = None):
        self.constructor_args = constructor_args
        self.gen = gen
        self.opt = opt
        self.lst = lst
        self.key = key
        self.name = name
        self.value = value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "key": self.key.to_dict() if self.key else None,
            "value": self.value.to_dict() if self.value else None,
            "lst": self.lst.to_dict() if self.lst else None,
            "opt": self.opt.to_dict() if self.opt else None,
            "gen": self.gen.to_dict() if self.gen else None,
            "constructor_args": [c.to_dict() for c in self.constructor_args if c] if self.constructor_args else None
        }


class ConfigItem:
    def __init__(self,
                 key: str,
                 value: object):
        self.value = value
        self.key = key


class ConfigDefinition:
    def __init__(self,
                 name: str,
                 class_def: ClassDef,
                 file: str):
        self.class_def = class_def
        self.file = file
        self.name = name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "class_def": self.class_def.to_dict() if self.class_def else None,
            "file": self.file
        }


ToReflectT = TypeVar("ToReflectT", covariant=True, bound=Reflectable)


class ReflectableModuleDefinition(Generic[ToReflectT]):
    def __init__(self,
                 class_def: ClassDef,
                 file: Optional[str] = None,
                 module: Optional[str] = None,
                 configs: list[ToReflectT] = None,
                 module_definitions: list = None):
        self.module = module
        self.class_def = class_def
        self.module_definitions = module_definitions
        self.file = file
        self.configs = configs if configs else []

    def to_dict(self) -> dict:
        return {
            "class_def": self.class_def.to_dict(),
            "file": self.file,
            "module": self.module,
            "configs": [c.to_dict() for c in self.configs if c],
            "module_definitions": [m.to_dict() for m in self.module_definitions if
                                   m] if self.module_definitions else None
        }


class ModuleDefinition(ReflectableModuleDefinition[ConfigDefinition]):
    def __init__(self, class_def: ClassDef, file: Optional[str] = None, module: Optional[str] = None,
                 configs: list[ConfigDefinition] = None, module_definitions: list = None):
        super().__init__(class_def, file, module, configs, module_definitions)
        self.module = module
        self.class_def = class_def
        self.module_definitions = module_definitions
        self.file = file
        self.configs = configs if configs else []

    def to_dict(self) -> dict:
        return {
            "class_def": self.class_def.to_dict(),
            "file": self.file,
            "module": self.module,
            "configs": [c.to_dict() for c in self.configs if c],
            "module_definitions": [m.to_dict() for m in self.module_definitions if
                                   m] if self.module_definitions else None
        }


class ModuleImport:
    def __init__(self,
                 module: str,
                 classes_imported: list[str] = None,
                 name: Optional[str] = None):
        self.classes_imported = classes_imported
        self.module = module
        self.name = name
