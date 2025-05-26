import os
import typing

from python_di.reflect_scanner.import_resolver.language_import_resolver import (
    LanguageImportResolver, LanguageDetector, Language, ImportResolverFactory
)
from python_di.reflection.resolve_src import ImportType
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom, ProgramNode, NodeType
from python_util.logger.logger import LoggerFacade
from python_util.io_utils.file_dirs import get_base_path_of_current_file


class PythonImportResolver(LanguageImportResolver):
    """
    Resolves Python imports according to Python's import resolution rules.
    """
    
    def supports_language(self, file_path: str) -> bool:
        """Determines if this resolver supports Python files."""
        return LanguageDetector.detect_language(file_path) == Language.PYTHON
    
    def resolve_module_import(self, import_type: ImportType, 
                              node: Import | ImportFrom, 
                              source_file: str) -> typing.Union[str, typing.List[str]]:
        """
        Resolves a Python import statement to the corresponding file(s).
        
        Args:
            import_type: The type of import (absolute, relative, etc.)
            node: The import node from the AST
            source_file: The file containing the import statement
            
        Returns:
            A single file path or list of file paths that correspond to the import
        """
        try:
            if import_type == ImportType.AbsoluteImport:
                return self._resolve_absolute_import(node, source_file)
            elif import_type == ImportType.ExplicitRelativeImport:
                return self._resolve_relative_import(node, source_file)
            elif import_type == ImportType.AliasImport:
                return self._resolve_alias_import(node, source_file)
            elif import_type == ImportType.SelectiveImport:
                return self._resolve_selective_import(node, source_file)
            elif import_type == ImportType.MultipleImport:
                return self._resolve_multiple_import(node, source_file)
            elif import_type == ImportType.WildcardImport:
                return self._resolve_wildcard_import(node, source_file)
            else:
                LoggerFacade.warn(f"Unsupported import type {import_type} in {source_file}")
                return []
        except Exception as e:
            LoggerFacade.error(f"Error resolving import in {source_file}: {e}")
            return []
    
    def resolve_type_reference(self, type_reference: str, 
                               source_file: str, 
                               imports: typing.List[Import | ImportFrom]) -> str:
        """
        Resolves a type reference to its fully qualified name using available imports.
        
        Args:
            type_reference: The type reference (e.g. class name)
            source_file: The file containing the reference
            imports: List of imports available in the source file
            
        Returns:
            The fully qualified name of the referenced type
        """
        # Check if the reference already contains a module path
        if '.' in type_reference:
            # It's already a qualified reference, so return it as is
            return type_reference
        
        # Look for the type in imports
        for imp in imports:
            if isinstance(imp, Import):
                # Handle 'import module' case
                for name in imp.name:
                    if name.endswith('.' + type_reference) or name == type_reference:
                        return name
            elif isinstance(imp, ImportFrom):
                # Handle 'from module import name' case
                if type_reference in imp.name:
                    return f"{imp.module}.{type_reference}"
        
        # If not found in imports, assume it's in the same file
        return type_reference
    
    def _resolve_absolute_import(self, node: Import, source_file: str) -> str:
        """Resolve an absolute import like 'import module'."""
        module_path = node.name[0].replace('.', os.path.sep)
        base_dir = os.path.dirname(source_file)
        
        # Search for the module in the Python path
        possible_paths = [
            f"{base_dir}/{module_path}.py",
            f"{base_dir}/{module_path}/__init__.py"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If module not found, return the original module name
        # so it can be handled by external resolution
        return node.name[0]
    
    def _resolve_relative_import(self, node: ImportFrom, source_file: str) -> str:
        """Resolve a relative import like 'from .module import name'."""
        # Calculate the base directory based on the relative level
        base_dir = os.path.dirname(source_file)
        for _ in range(node.level):
            base_dir = os.path.dirname(base_dir)
        
        # Construct the path to the imported module
        if node.module:
            module_path = node.module.replace('.', os.path.sep)
            full_path = f"{base_dir}/{module_path}.py"
            
            if os.path.exists(full_path):
                return full_path
            
            # Check for package
            init_path = f"{base_dir}/{module_path}/__init__.py"
            if os.path.exists(init_path):
                return init_path
        else:
            # Import from parent package without module name
            init_path = f"{base_dir}/__init__.py"
            if os.path.exists(init_path):
                return init_path
        
        # If module not found, construct a best-guess path
        return f"{base_dir}/{node.module if node.module else ''}"
    
    def _resolve_alias_import(self, node: Import, source_file: str) -> str:
        """Resolve an import with alias like 'import module as alias'."""
        # The resolution is the same as absolute import
        return self._resolve_absolute_import(node, source_file)
    
    def _resolve_selective_import(self, node: ImportFrom, source_file: str) -> str:
        """Resolve a selective import like 'from module import name1, name2'."""
        # The resolution is similar to relative import but we also need to handle the names
        if node.level > 0:
            return self._resolve_relative_import(node, source_file)
        else:
            # Handle absolute import from
            module_path = node.module.replace('.', os.path.sep)
            base_dir = os.path.dirname(source_file)
            
            possible_paths = [
                f"{base_dir}/{module_path}.py",
                f"{base_dir}/{module_path}/__init__.py"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            return node.module
    
    def _resolve_multiple_import(self, node: Import, source_file: str) -> typing.List[str]:
        """Resolve multiple imports like 'import module1, module2'."""
        resolved = []
        for name in node.name:
            module_path = name.replace('.', os.path.sep)
            base_dir = os.path.dirname(source_file)
            
            possible_paths = [
                f"{base_dir}/{module_path}.py",
                f"{base_dir}/{module_path}/__init__.py"
            ]
            
            found = False
            for path in possible_paths:
                if os.path.exists(path):
                    resolved.append(path)
                    found = True
                    break
            
            if not found:
                resolved.append(name)
        
        return resolved
    
    def _resolve_wildcard_import(self, node: ImportFrom, source_file: str) -> typing.List[str]:
        """Resolve wildcard import like 'from module import *'."""
        # First, resolve the module itself
        if node.level > 0:
            module_path = self._resolve_relative_import(node, source_file)
        else:
            module_path = node.module.replace('.', os.path.sep)
            base_dir = os.path.dirname(source_file)
            
            possible_paths = [
                f"{base_dir}/{module_path}.py",
                f"{base_dir}/{module_path}/__init__.py"
            ]
            
            found = False
            for path in possible_paths:
                if os.path.exists(path):
                    module_path = path
                    found = True
                    break
            
            if not found:
                return [node.module]
        
        # For wildcard imports, we'd ideally parse the target module
        # and get all exportable names, but that's complex.
        # Instead, we'll just return the module path for now.
        return [module_path]


# Register the resolver with the factory
ImportResolverFactory.register_resolver(PythonImportResolver())