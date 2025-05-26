import os
import typing
import re
from pathlib import Path

from python_di.reflect_scanner.import_resolver.language_import_resolver import (
    LanguageImportResolver, LanguageDetector, Language, ImportResolverFactory
)
from python_di.reflection.resolve_src import ImportType
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom, ProgramNode, NodeType
from python_util.logger.logger import LoggerFacade


class JavaImportResolver(LanguageImportResolver):
    """
    Resolves Java imports according to Java's import resolution rules.
    """
    
    # Java standard library packages that are implicitly available
    IMPLICIT_PACKAGES = [
        "java.lang"
    ]
    
    def supports_language(self, file_path: str) -> bool:
        """Determines if this resolver supports Java files."""
        return LanguageDetector.detect_language(file_path) == Language.JAVA
    
    def resolve_module_import(self, import_type: ImportType, 
                              node: Import | ImportFrom, 
                              source_file: str) -> typing.Union[str, typing.List[str]]:
        """
        Resolves a Java import statement to the corresponding file(s).
        
        Args:
            import_type: The type of import 
            node: The import node from the AST
            source_file: The file containing the import statement
            
        Returns:
            A single file path or list of file paths that correspond to the import
        """
        try:
            if import_type == ImportType.AbsoluteImport:
                return self._resolve_java_import(node, source_file)
            elif import_type == ImportType.AliasImport:
                return self._resolve_java_import(node, source_file)
            elif import_type == ImportType.SelectiveImport:
                return self._resolve_java_import(node, source_file, selective=True)
            elif import_type == ImportType.WildcardImport:
                return self._resolve_wildcard_import(node, source_file)
            else:
                LoggerFacade.warn(f"Unsupported Java import type {import_type} in {source_file}")
                return []
        except Exception as e:
            LoggerFacade.error(f"Error resolving Java import in {source_file}: {e}")
            return []
    
    def resolve_type_reference(self, type_reference: str, 
                               source_file: str, 
                               imports: typing.List[Import | ImportFrom]) -> str:
        """
        Resolves a Java type reference to its fully qualified name using available imports.
        
        Args:
            type_reference: The type reference (e.g. class name, interface name)
            source_file: The file containing the reference
            imports: List of imports available in the source file
            
        Returns:
            The fully qualified name of the referenced type
        """
        # If it's already a fully qualified name, return it
        if '.' in type_reference and not type_reference.startswith('.'):
            return type_reference
        
        # Extract the simple name (without generics)
        simple_name = re.sub(r'<.*>', '', type_reference).strip()
        
        # Check explicit imports
        for imp in imports:
            if isinstance(imp, Import):
                # Handle regular import
                for name in imp.name:
                    if name.endswith('.' + simple_name):
                        return name
            elif isinstance(imp, ImportFrom) and imp.module:
                # Handle static imports and selective imports
                if simple_name in imp.name:
                    return f"{imp.module}.{simple_name}"
                
                # Check for wildcard imports
                if '*' in imp.name:
                    # We'd need to check if the type exists in this package
                    # For now, return a qualified guess
                    return f"{imp.module}.{simple_name}"
        
        # Check if it's in the same package as the source file
        source_package = self._extract_package_from_file(source_file)
        if source_package:
            # Check if the type exists in the same package
            potential_file = self._find_java_file_in_package(source_package, simple_name)
            if potential_file:
                return f"{source_package}.{simple_name}"
        
        # Check implicit packages (java.lang.*)
        for pkg in self.IMPLICIT_PACKAGES:
            potential_file = self._find_java_file_in_package(pkg, simple_name)
            if potential_file:
                return f"{pkg}.{simple_name}"
        
        # If not found, return the original type reference
        return type_reference
    
    def _resolve_java_import(self, node: Import | ImportFrom, source_file: str, selective: bool = False) -> str:
        """Resolve a Java import statement."""
        if isinstance(node, Import):
            # Regular import: import package.Class
            import_name = node.name[0]
        else:
            # Static or selective import: from package import Class
            import_name = node.module
            
            if selective and node.name:
                # For selective imports, append the class name
                import_name = f"{import_name}.{node.name[0]}"
        
        # Convert package path to file path
        source_dir = self._get_project_root(source_file)
        package_path = import_name.replace('.', os.path.sep)
        
        # Look for .java file
        java_file = f"{source_dir}/{package_path}.java"
        if os.path.exists(java_file):
            return java_file
        
        # Look for package directory
        package_dir = f"{source_dir}/{os.path.dirname(package_path)}"
        if os.path.exists(package_dir):
            return package_dir
        
        # If not found, return the import name for external resolution
        return import_name
    
    def _resolve_wildcard_import(self, node: ImportFrom, source_file: str) -> typing.List[str]:
        """Resolve a wildcard import like 'import package.*'."""
        # Get the package name
        package_name = node.module
        
        # Convert package to directory path
        source_dir = self._get_project_root(source_file)
        package_path = package_name.replace('.', os.path.sep)
        package_dir = f"{source_dir}/{package_path}"
        
        # If directory exists, find all Java files in it
        if os.path.exists(package_dir):
            java_files = []
            for file in os.listdir(package_dir):
                if file.endswith('.java'):
                    java_files.append(f"{package_dir}/{file}")
            return java_files
        
        # If not found, return the package name
        return [package_name]
    
    def _extract_package_from_file(self, file_path: str) -> typing.Optional[str]:
        """Extract the package declaration from a Java file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Simple regex to extract package name
            match = re.search(r'package\s+([\w.]+);', content)
            if match:
                return match.group(1)
        except Exception as e:
            LoggerFacade.error(f"Error extracting package from {file_path}: {e}")
        
        return None
    
    def _find_java_file_in_package(self, package_name: str, class_name: str) -> typing.Optional[str]:
        """Find a Java file in a package directory."""
        # This is a stub implementation
        # In a real implementation, we would search project directories and classpath
        return None
    
    def _get_project_root(self, file_path: str) -> str:
        """
        Get the project root directory.
        This is a simplified implementation that assumes the source file is in a Java project.
        """
        # In a real implementation, we would look for markers like pom.xml, build.gradle, etc.
        # For now, just return the parent directory of the source file
        return os.path.dirname(file_path)


# Register the resolver with the factory
ImportResolverFactory.register_resolver(JavaImportResolver())