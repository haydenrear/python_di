import ast
import unittest

from python_di.inject.context_builder.injection_context import InjectionContext
from python_di.reflect_scanner.ast_utils import parse_ast_into_file
from python_di.reflect_scanner.statements_parser import AggregateStatementParser


class StatementParserTest(unittest.TestCase):
    def test_injection(self):
        agg: AggregateStatementParser = InjectionContext.get_interface(AggregateStatementParser)
        assert agg
        parsed = parse_ast_into_file(__file__)
        for child in ast.iter_child_nodes(parsed):
            if isinstance(child, ast.stmt):
                assert agg.parse_statement_node(child, 'hello')





if __name__ == '__main__':
    unittest.main()
