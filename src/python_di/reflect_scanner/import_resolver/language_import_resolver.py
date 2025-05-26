import abc
import os
import typing
from enum import Enum, auto

from python_di.reflection.resolve_src import ImportType
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom, ProgramNode, NodeType
from python_util.logger.logger import LoggerFacade


class Language(Enum):
    JAVA = auto()
    PYTHON = auto()
    UNKNOWN = auto()


class LanguageDetector:
    """Detects the language of a file based on its extension."""
    
    EXTENSION_MAP = {
        '.java': Language.JAVA,
        '.py': Language.PYTHON,
    }
    
    @staticmethod
    def detect_language(file_path: str) -> Language:
        """Detect the language of a file based on its extension."""
        _, ext = os.path.splitext(file_path)
        return LanguageDetector.EXTENSION_MAP.get(ext.lower(), Language.UNKNOWN)


class LanguageImportResolver(abc.ABC):
    """
    Base class for language-specific import resolvers.
    Each language implementation should extend this class.
    """
    
    @abc.abstractmethod
    def supports_language(self, file_path: str) -> bool:
        """
        Determines if this resolver supports the given file's language.
        
        Args:
            file_path: The path to the file
            
        Returns:
            True if this resolver can handle imports for this file type
        """
        pass
    
    @abc.abstractmethod
    def resolve_module_import(self, import_type: ImportType, 
                              node: Import | ImportFrom, 
                              source_file: str) -> typing.Union[str, typing.List[str]]:
        """
        Resolves an import statement to the corresponding file(s).
        
        Args:
            import_type: The type of import (absolute, relative, etc.)
            node: The import node from the AST
            source_file: The file containing the import statement
            
        Returns:
            A single file path or list of file paths that correspond to the import
        """
        pass
    
    @abc.abstractmethod
    def resolve_type_reference(self, type_reference: str, 
                               source_file: str, 
                               imports: typing.List[Import | ImportFrom]) -> str:
        """
        Resolves a type reference to its fully qualified name using available imports.
        
        Args:
            type_reference: The type reference (e.g. class name, interface name)
            source_file: The file containing the reference
            imports: List of imports available in the source file
            
        Returns:
            The fully qualified name of the referenced type
        """
        pass


class ImportResolverFactory:
    """Factory for creating language-specific import resolvers."""
    
    _resolvers: typing.List[LanguageImportResolver] = []
    
    @classmethod
    def register_resolver(cls, resolver: LanguageImportResolver):
        """Register a language-specific import resolver."""
        cls._resolvers.append(resolver)
    
    @classmethod
    def get_resolver(cls, file_path: str) -> typing.Optional[LanguageImportResolver]:
        """Get the appropriate resolver for the given file."""
        for resolver in cls._resolvers:
            if resolver.supports_language(file_path):
                return resolver
        
        # Log if no suitable resolver is found
        LoggerFacade.warn(f"No import resolver found for {file_path}")
        return None