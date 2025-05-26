import abc
import dataclasses
import enum
import typing
from enum import Enum, auto

from python_di.reflect_scanner.type_introspector import IntrospectedDef


class SerializableEnum(enum.Enum):
    @classmethod
    def value_of(cls, value: str):
        for i, name in cls.__members__.items():
            if i.lower() == value.lower():
                return name


class Language(SerializableEnum):
    PYTHON = auto()
    JAVA = auto()
    UNKNOWN = auto()


class GraphElement(Enum):
    NODE = auto()
    EDGE = auto()


class NodeType(Enum):
    STATEMENT = auto()
    IMPORT = auto()
    IMPORT_FROM = auto()
    IMPORTED_DEPENDENCY = auto()
    SAME_SRC_DEPENDENCY = auto()
    CLASS = auto()
    ARG = auto()
    FUNCTION = auto()
    NAME = auto()
    ATTRIBUTE = auto()
    MODULE = auto()
    PATH = auto()
    BASE_CLASS = auto()
    TYPE_CONNECTION = auto()
    DECORATOR = enum.auto()


class Node(abc.ABC):
    @property
    @abc.abstractmethod
    def node_type(self) -> NodeType:
        pass


class GraphType(enum.Enum):
    File = enum.auto()
    Program = enum.auto()


@dataclasses.dataclass(eq=True)
class ProgramNode(Node):
    def __init__(self,
                 node_type: NodeType,
                 source_file: str,
                 id_value: str,
                 line_no: int = -1):
        self.line_no = line_no
        self.id_value = id_value
        self.source_file = source_file
        self._node_type = node_type

    @property
    def node_type(self) -> NodeType:
        return self._node_type

    def __hash__(self):
        return hash((self._node_type, self.id_value, self.source_file))

    def __str__(self):
        return str(self.node_type)


class TypeConnectionProgramNode(ProgramNode):
    def __init__(self, source_file: str, id_value: str, introspected_def: IntrospectedDef, line_no: int = 0):
        super().__init__(NodeType.TYPE_CONNECTION, source_file, id_value, line_no)
        self.introspected_def = introspected_def


class FileNode(Node):

    def __init__(self, node_type: NodeType, id_value: str):
        self.id_value = id_value
        self._node_type = node_type

    @property
    def node_type(self) -> NodeType:
        return self._node_type

    def __hash__(self):
        return hash((self.node_type, self.id_value))

    def __eq__(self, other):
        if not hasattr(other, 'node_type') or not hasattr(other, 'id_value'):
            return False
        return other.node_type == self.node_type and other.id_value == self.id_value

    def __str__(self):
        return f'Node type: {self.node_type}\nId value: {self.id_value}'


@dataclasses.dataclass(eq=True)
class ClassFunctionProgramNode(ProgramNode):
    def __init__(self, class_id: str, source_file: str,
                 id_value: str = '__init__', line_no: int = 0):
        super().__init__(NodeType.FUNCTION, source_file, id_value)
        self.class_id = class_id

    def __hash__(self):
        return hash((self.node_type, self.id_value, self.source_file, self.class_id))


@dataclasses.dataclass(eq=True)
class DecoratorProgramNode(ProgramNode):
    def __init__(self, decorator_id: str, decorated_id: str, source_file: str, decorated_ty: NodeType):
        super().__init__(NodeType.DECORATOR, source_file, decorator_id)
        self.decorated_id = decorated_id
        self.decorated_ty = decorated_ty

    def __hash__(self):
        return hash((self.node_type, self.id_value, self.source_file, self.decorated_id, self.decorated_ty))


class StatementType(SerializableEnum):
    While = auto()
    List = auto()
    Tuple = auto()
    Name = auto()
    Starred = auto()
    Subscript = auto()
    Attribute = auto()
    Constant = auto()
    JoinedStr = auto()
    FormattedValue = auto()
    Call = auto()
    Compare = auto()
    YieldFrom = auto()
    Yield = auto()
    Await = auto()
    GeneratorExp = auto()
    DictComp = auto()
    SetComp = auto()
    ListComp = auto()
    Set = auto()
    Dict = auto()
    IfExp = auto()
    Lambda = auto()
    UnaryOp = auto()
    BinOp = auto()
    BoolOp = auto()
    Continue = auto()
    Break = auto()
    Pass = auto()
    Expr = auto()
    NonLocal = auto()
    Global = auto()
    ImportFrom = auto()
    Import = auto()
    Assert = auto()
    Try = auto()
    Raise = auto()
    AsyncWith = auto()
    With = auto()
    AsyncFor = auto()
    AnnAssign = auto()
    AugAssign = auto()
    Assign = auto()
    Delete = auto()
    Return = auto()
    ClassDef = auto()
    AsyncFunctionDef = auto()
    FunctionDef = auto()
    If = auto()
    For = auto()


class Statement:
    def __init__(self,
                 statement_type: StatementType,
                 statement_id: str,
                 lin_no: int,
                 statements: list,
                 statement_str: typing.Optional[str] = None,
                 ids: list[str] = None):
        """

        :param statement_type:
        :param statement_id:
        :param lin_no:
        :param statements:
        :param statement_str:
        :param ids: Ids of items in the statement, to connect the statement to the import node or within-file nodes
        """
        self.statement_str = statement_str
        self.lin_no = lin_no
        self.statements = statements
        self.statement_type = statement_type
        self.statement_id = statement_id
        self.ids = ids


class StatementNode(FileNode):
    def __init__(self, id_value, statements: list[Statement]):
        super().__init__(NodeType.STATEMENT, id_value)
        self.statements = statements


class ProgramStatementNode(ProgramNode):
    def __init__(self, source_code: str, id_value, statements: list[Statement], source_file: str):
        super().__init__(NodeType.STATEMENT, source_file, id_value, source_code)
        self.statements = statements


class IntrospectedPathNode(FileNode):
    def __init__(self, id_value: str, introspected: IntrospectedDef):
        super().__init__(NodeType.PATH, id_value)
        self.introspected = introspected


class ClassFunctionFileNode(FileNode):
    def __init__(self, class_id: str, id_value: str = '__init__'):
        super().__init__(NodeType.FUNCTION, id_value)
        self.class_id = class_id


class DecoratorFileNode(FileNode):
    def __init__(self, decorated_id: str, id_value: str, decorated_ty: NodeType):
        super().__init__(NodeType.DECORATOR, id_value)
        self.decorated_id = decorated_id
        self.decorated_ty = decorated_ty


class ArgFileNode(FileNode):
    def __init__(self, id_value: str, introspected: typing.List[IntrospectedDef]):
        super().__init__(NodeType.ARG, id_value)
        self.introspected = introspected

    def __hash__(self):
        return hash((self.node_type, self.id_value, tuple(self.introspected)))

    def __str__(self):
        return f'Node type: {self.node_type}\nId value: {self.id_value}'


class GraphItem:
    def __init__(self, element_type: GraphElement,
                 node_type: NodeType, value):
        self.element_type = element_type
        self.node_type = node_type
        self.value = value


class Import(FileNode):
    def __init__(self,
                 name: list[str] = None,
                 as_name: list[str] = None):
        self.import_str = f"import {', '.join(name)}"
        if as_name is not None and len(as_name) != 0:
            self.import_str += f" as {', '.join(as_name)}"
        super().__init__(NodeType.IMPORT, self.import_str)
        self.as_name = as_name
        self.name = name
        self.language = Language.UNKNOWN  # Will be set by ImportParser

    def __hash__(self):
        return hash((self.import_str, tuple(self.name), tuple(self.as_name)))

    def __str__(self):
        return f'{super().__str__()}\nAs name: {self.as_name}\nName: {self.name}\nImport str: {self.import_str}'


class ImportFrom(FileNode):
    def __init__(self, name: list[str] = None, as_name: list[str] = None,
                 module: str | None = None, level: int = 0):
        self.import_str = f"from {module} import {', '.join(name)}"
        if as_name is not None and len(as_name) != 0:
            self.import_str += f" as {', '.join(as_name)}"
        super().__init__(NodeType.IMPORT_FROM, self.import_str)
        self.level = level
        self.module = module
        self.as_name = as_name
        self.name = name
        self.language = Language.UNKNOWN  # Will be set by ImportParser

    def __hash__(self):
        return hash((self.import_str, tuple(self.name), tuple(self.as_name), self.module, self.level))
