import ast
import os.path
import unittest

from python_di.inject.injector_provider import InjectionContext
from python_di.reflect_scanner.ast_utils import parse_ast_into_file
from python_di.reflect_scanner.module_config_models import ClassDef
from python_di.reflect_scanner.type_introspector import AggregateTypeIntrospecter, IntrospectedOptional, \
    IntrospectedList


class AggregateTypeIntrospecterTest(unittest.TestCase):
    def test_get_type(self):
        agg = InjectionContext.get_interface(AggregateTypeIntrospecter)
        assert agg
        to_test = os.path.join(os.path.dirname(__file__), 'to_parse_test_file.py')

        parsed = parse_ast_into_file(to_test)
        to_test = self.get_introspected(agg, parsed)
        introspected_str = to_test['TestStr']
        assert len(introspected_str) == 1
        assert introspected_str[0].name == 'str'

        introspected_opt = to_test['TestOptional']
        assert len(introspected_opt) == 1
        assert introspected_opt[0].opt_type.name == 'str'

        introspected_dct = to_test['TestDict']
        assert len(introspected_dct) == 1
        assert introspected_dct[0].key.name == 'str'
        assert introspected_dct[0].value.name == 'str'

        introspected_dct_of_lst = to_test['TestDictOfList']
        assert len(introspected_dct_of_lst) == 1
        assert introspected_dct_of_lst[0].key.name == 'str'
        assert isinstance(introspected_dct_of_lst[0].value, IntrospectedList)

        introspected_lst = to_test['TestList']
        assert len(introspected_lst) == 1
        assert introspected_lst[0].list_values.name == 'str'

        for i in introspected_lst:
            deps = i.get_class_deps()
            print(deps)

        tree = to_test['TestDictOfList'][0].get_introspected_tree()
        assert tree['dict[str,list[str]]']['self_param'].name == 'dict[str,list[str]]'
        assert tree['dict[str,list[str]]']['self_param'].key.name == 'str'
        assert tree['dict[str,list[str]]']['str']['self_param'].name == 'str'



    def get_introspected(self, agg, parsed):
        to_test = {}
        for node in ast.iter_child_nodes(parsed):
            if isinstance(node, ast.ClassDef):
                for body in node.body:
                    if isinstance(body, ast.FunctionDef) and body.name == '__init__':
                        for arg in body.args.args:
                            if isinstance(arg, ast.arg):
                                introspected = agg.introspect_type(arg.annotation)
                                to_test[node.name] = introspected
        return to_test





