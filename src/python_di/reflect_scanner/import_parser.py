import ast

from python_di.reflect_scanner.file_parser import ASTNodeParser
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom


class ImportParser(ASTNodeParser):
    """
    TODO: connect import to each of the things referencing it on second pass
    Adds nodes between the source file and the imports within that source file.
    """

    def matches(self, node) -> bool:
        return isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom)

    def parse(self, node, graph, source, parser=None, parent=None):
        assert parser is not None
        if isinstance(node, ast.Import):
            name = [name.name for name in node.names if name.name]
            as_name = [name.asname for name in node.names if name.asname]
            import_val = Import(name, as_name)
            graph.add_node(import_val)
            graph.add_edge(parent, import_val)
        elif isinstance(node, ast.ImportFrom):
            name = [name.name for name in node.names if name.name]
            as_name = [name.asname for name in node.names if name.asname]
            import_val = ImportFrom(name, as_name, node.module,
                                    node.level)
            graph.add_node(import_val)
            graph.add_edge(parent, import_val)
