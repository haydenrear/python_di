import importlib
import unittest
import ast

from python_di.reflect_scanner.file_parser import retrieve_source_files
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom
from python_di.reflect_scanner.program_parser import determine_import_type
from python_di.reflection.resolve_src import get_module_path, ImportResolver


class ReflectionTest(unittest.TestCase):
    def test_resolve(self):
        out = get_module_path("torch.nn.Module")
        print(out)

    def test_retrieve_file(self):
        out = retrieve_source_files("torch.nn")
        assert out is not None

    def test_import_resolver(self):
        importlib.import_module('python_di.reflect_scanner.file_parser', 'retrieve_source_files')
        with open(__file__, 'r') as file_read:
            parsed = ast.parse('\n'.join(file_read.readlines()))
            for node in ast.iter_child_nodes(parsed):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    i = Import([a.name for a in node.names])
                    import_type = determine_import_type(i)
                    resolved = ImportResolver.resolve_module_import(import_type, node, __file__)
                    assert resolved


if __name__ == '__main__':
    unittest.main()
