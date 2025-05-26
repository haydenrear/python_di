import ast
import os

from python_di.reflect_scanner.file_parser import ASTNodeParser
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom, Language
from python_di.reflect_scanner.import_resolver.language_import_resolver import LanguageDetector


class ImportParser(ASTNodeParser):
    """
    Adds nodes between the source file and the imports within that source file.
    Handles imports from different languages by converting them to a common representation.
    """

    def matches(self, node) -> bool:
        return isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom)

    def parse(self, node, graph, source, parser=None, parent=None):
        assert parser is not None
        
        # Determine the language of the source file
        detected_language = LanguageDetector.detect_language(source)
        # Convert to our module_graph_models.Language enum
        if detected_language == LanguageDetector.EXTENSION_MAP.get('.java'):
            language = Language.JAVA
        elif detected_language == LanguageDetector.EXTENSION_MAP.get('.py'):
            language = Language.PYTHON
        else:
            language = Language.UNKNOWN
        
        if isinstance(node, ast.Import):
            name = [name.name for name in node.names if name.name]
            as_name = [name.asname for name in node.names if name.asname]
            import_val = Import(name, as_name)
            import_val.language = language  # Store the language for later resolution
            graph.add_node(import_val)
            graph.add_edge(parent, import_val)
        elif isinstance(node, ast.ImportFrom):
            name = [name.name for name in node.names if name.name]
            as_name = [name.asname for name in node.names if name.asname]
            import_val = ImportFrom(name, as_name, node.module,
                                    node.level)
            import_val.language = language  # Store the language for later resolution
            graph.add_node(import_val)
            graph.add_edge(parent, import_val)
