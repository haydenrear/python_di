import unittest
import ast

from python_di.reflect_scanner.file_parser import retrieve_source_files
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
        with open(__file__, 'r') as file_read:
            parsed = ast.parse('\n'.join(file_read.readlines()))
            for node in ast.iter_child_nodes(parsed):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_type = determine_import_type(node)
                    resolved = ImportResolver.resolve_module_import(import_type, node, __file__)
                    with open(resolved, 'r') as r:
                        parsed = ast.parse('\n'.join(r.readlines()))
                    print(resolved)


if __name__ == '__main__':
    unittest.main()
