import abc
import ast
import typing
import injector
import networkx as nx

from python_di.reflect_scanner.module_graph_models import StatementNode, Statement, StatementType


class StatementParser(abc.ABC):
    def __init__(self):
        self.agg_stmt_parser: typing.Optional[AggregateStatementParser] = None

    @abc.abstractmethod
    def matches(self, stmt: ast.stmt):
        pass

    @abc.abstractmethod
    def parse_statement(self, stmt: ast.stmt, id_value: str) -> Statement:
        pass

    def set_aggregate(self, agg):
        self.agg_stmt_parser = agg

    def parse_fields(self, stmt: ast.AST, id_value: str) -> typing.List[Statement]:
        stmts = []
        self.parse_item(id_value, stmts, id_value)
        for field, value in ast.iter_fields(stmt):
            self.parse_item(id_value, stmts, value)

        return stmts

    def parsed_str(self, stmt):
        for field, value in ast.iter_fields(stmt):
            if isinstance(value, str):
                return value


    def parse_item(self, id_value, stmts, value):
        if isinstance(value, list | typing.Iterable | typing.Iterator):
            for item in value:
                if isinstance(item, ast.stmt | ast.expr):
                    parsed = self.agg_stmt_parser.parse_statement(item, id_value)
                    if parsed:
                        stmts.append(parsed)
        elif isinstance(value, ast.stmt | ast.expr):
            parsed = self.agg_stmt_parser.parse_statement(value, id_value)
            if parsed:
                stmts.append(parsed)


class AggregateStatementParser(StatementParser):

    @injector.inject
    def __init__(self, statement_parsers: typing.List[StatementParser]):
        super().__init__()
        self.statement_parsers = statement_parsers
        for p in self.statement_parsers:
            p.set_aggregate(self)

    def parse_statement_node(self, stmt: typing.Union[ast.stmt, typing.List[ast.stmt]],
                             id_value: str,
                             graph: nx.DiGraph = None) -> StatementNode:
        """
        Each statement node contains child statements and statement nodes which can reference imports - any statement node
        that that could reference an import, class, or function has a connection between that node and a delegate node to the import, no matter how deep in the graph,
        and then can bubble up to the parent node to parse the AST around.

        The connection between the node and the import will not be the import node, but a connecting node, and the adding of this node to the graph will be idempotent
        and then at the end a connection will be added from this idempotent node to the actual import. This makes it so that you don't have to add the import
        node if you don't find it, and you can then find nodes that are not linked to imports.

        Then once you've parsed the connections between files, language dependent, added imports that didn't exist, then any dangling can be added, and when dangling
        are added you're already there so you can try to check for type inference (this is where type inference would need to be).

        Then you will have a quick connection between a symbol and everywhere it's implemented, because you have a map between
        a symbol and everywhere it's imported, and a map between the places it's imported and directly where it's used. Then there
        will also be a way to get the contextual AST from where it's used bubbling up to the parent statements or parent function.

        So this is JUST A HASHTABLE
        :param stmt:
        :param id_value:
        :param graph:
        :return:
        """
        if not isinstance(stmt, list):
            for parser in self.statement_parsers:
                if parser.matches(stmt):
                    parsed: Statement = parser.parse_statement(stmt, id_value)
                    return StatementNode(id_value, [parsed])

            return StatementNode(id_value, [])
        else:
            statements = []
            for stmt_ in stmt:
                for parser in self.statement_parsers:
                    if parser.matches(stmt_):
                        parsed: Statement = parser.parse_statement(stmt_, id_value)
                        statements.append(parsed)

            return StatementNode(id_value, statements)


    def parse_statement(self, stmt: ast.stmt, id_value: str) -> Statement:
        for parser in self.statement_parsers:
            if parser.matches(stmt):
                return parser.parse_statement(stmt, id_value)

    def matches(self, stmt: ast.stmt):
        return True


class IfStatementParser(StatementParser):
    def matches(self, stmt: ast.stmt):
        return isinstance(stmt, ast.If)

    def parse_statement(self, stmt: ast.If, id_value: str) -> Statement:
        stmts = self.parse_fields(stmt, id_value)
        return Statement(StatementType.If, id_value, stmt.lineno, stmts, self.parsed_str(stmt))


class ForStatementParser(StatementParser):
    def matches(self, stmt: ast.stmt):
        return isinstance(stmt, ast.For)

    def parse_statement(self, stmt: ast.For, id_value: str) -> Statement:
        stmts = self.parse_fields(stmt, id_value)
        return Statement(StatementType.For, id_value, stmt.lineno, stmts, self.parsed_str(stmt))


class WhileStatementParser(StatementParser):
    def matches(self, stmt: ast.stmt):
        return isinstance(stmt, ast.While)

    def parse_statement(self, stmt: ast.While, id_value: str) -> Statement:
        stmts = self.parse_fields(stmt, id_value)
        return Statement(StatementType.While, id_value, stmt.lineno, stmts, self.parsed_str(stmt))


class AttributeParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Attribute)

    def parse_statement(self, node: ast.Attribute, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Attribute, id_value, node.lineno, stmts, node.attr)


class ValueParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.FormattedValue)

    def parse_statement(self, node: ast.FormattedValue, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.FormattedValue, id_value, node.lineno, stmts, self.parsed_str(node))


class ConstantParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Constant)

    def parse_statement(self, node: ast.Constant, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Constant, id_value, node.lineno, stmts, self.parsed_str(node))


class FunctionDefParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.FunctionDef)

    def parse_statement(self, node: ast.FunctionDef, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.FunctionDef, id_value, node.lineno, stmts, self.parsed_str(node))


class AsyncFunctionDefParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.AsyncFunctionDef)

    def parse_statement(self, node: ast.AsyncFunctionDef, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.AsyncFunctionDef, id_value, node.lineno, stmts, self.parsed_str(node))


class ClassDefParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.ClassDef)

    def parse_statement(self, node: ast.ClassDef, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.ClassDef, id_value, node.lineno, stmts, self.parsed_str(node))


class ReturnParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Return)

    def parse_statement(self, node: ast.Return, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Return, id_value, node.lineno, stmts, self.parsed_str(node))


class DeleteParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Delete)

    def parse_statement(self, node: ast.Delete, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Delete, id_value, node.lineno, stmts, self.parsed_str(node))


class AssignParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Assign)

    def parse_statement(self, node: ast.Assign, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Assign, id_value, node.lineno, stmts, self.parsed_str(node))


class AugAssignParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.AugAssign)

    def parse_statement(self, node: ast.AugAssign, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.AugAssign, id_value, node.lineno, stmts, self.parsed_str(node))


class AnnAssignParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.AnnAssign)

    def parse_statement(self, node: ast.AnnAssign, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.AnnAssign, id_value, node.lineno, stmts, self.parsed_str(node))


class AsyncForParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.AsyncFor)

    def parse_statement(self, node: ast.AsyncFor, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.AsyncFor, id_value, node.lineno, stmts, self.parsed_str(node))


class WithParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.With)

    def parse_statement(self, node: ast.With, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.With, id_value, node.lineno, stmts, self.parsed_str(node))


class AsyncWithParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.AsyncWith)

    def parse_statement(self, node: ast.AsyncWith, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.AsyncWith, id_value, node.lineno, stmts, self.parsed_str(node))


class RaiseParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Raise)

    def parse_statement(self, node: ast.Raise, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Raise, id_value, node.lineno, stmts, self.parsed_str(node))


class TryParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Try)

    def parse_statement(self, node: ast.Try, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Try, id_value, node.lineno, stmts, self.parsed_str(node))


class AssertParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Assert)

    def parse_statement(self, node: ast.Assert, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Assert, id_value, node.lineno, stmts, self.parsed_str(node))


class ImportParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Import)

    def parse_statement(self, node: ast.Import, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Import, id_value, node.lineno, stmts, self.parsed_str(node))


class ImportFromParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.ImportFrom)

    def parse_statement(self, node: ast.ImportFrom, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.ImportFrom, id_value, node.lineno, stmts, self.parsed_str(node))


class GlobalParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Global)

    def parse_statement(self, node: ast.Global, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Global, id_value, node.lineno, stmts, self.parsed_str(node))


class NonLocalParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Nonlocal)

    def parse_statement(self, node: ast.Nonlocal, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.NonLocal, id_value, node.lineno, stmts, self.parsed_str(node))


class ExprParser(StatementParser):
    def __init__(self):
        super().__init__()

    def matches(self, node: ast.AST):
        return isinstance(node, ast.Expr)

    def parse_statement(self, node: ast.Expr, id_value: str) -> Statement:
        stmts = self.parse_fields(node.value, id_value)
        return Statement(StatementType.Expr, id_value, node.lineno, stmts, self.parsed_str(node))


class PassParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Pass)

    def parse_statement(self, node: ast.Pass, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Pass, id_value, node.lineno, stmts, self.parsed_str(node))


class BreakParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Break)

    def parse_statement(self, node: ast.Break, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Break, id_value, node.lineno, stmts, self.parsed_str(node))


class ContinueParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Continue)

    def parse_statement(self, node: ast.Continue, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Continue, id_value, node.lineno, stmts, self.parsed_str(node))


class BoolOpParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.BoolOp)

    def parse_statement(self, node: ast.BoolOp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.BoolOp, id_value, node.lineno, stmts, self.parsed_str(node))


class BinOpParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.BinOp)

    def parse_statement(self, node: ast.BinOp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.BinOp, id_value, node.lineno, stmts, self.parsed_str(node))


class UnaryOpParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.UnaryOp)

    def parse_statement(self, node: ast.UnaryOp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.UnaryOp, id_value, node.lineno, stmts, self.parsed_str(node))


class LambdaParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Lambda)

    def parse_statement(self, node: ast.Lambda, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Lambda, id_value, node.lineno, stmts, self.parsed_str(node))


class IfExpParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.IfExp)

    def parse_statement(self, node: ast.IfExp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.IfExp, id_value, node.lineno, stmts, self.parsed_str(node))


class DictParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Dict)

    def parse_statement(self, node: ast.Dict, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Dict, id_value, node.lineno, stmts, self.parsed_str(node))


class SetParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Set)

    def parse_statement(self, node: ast.Set, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Set, id_value, node.lineno, stmts, self.parsed_str(node))


class ListCompParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.ListComp)

    def parse_statement(self, node: ast.ListComp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.ListComp, id_value, node.lineno, stmts, self.parsed_str(node))


class SetCompParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.SetComp)

    def parse_statement(self, node: ast.SetComp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.SetComp, id_value, node.lineno, stmts, self.parsed_str(node))


class DictCompParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.DictComp)

    def parse_statement(self, node: ast.DictComp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.DictComp, id_value, node.lineno, stmts, self.parsed_str(node))


class GeneratorExpParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.GeneratorExp)

    def parse_statement(self, node: ast.GeneratorExp, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.GeneratorExp, id_value, node.lineno, stmts, self.parsed_str(node))


class AwaitParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Await)

    def parse_statement(self, node: ast.Await, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Await, id_value, node.lineno, stmts, self.parsed_str(node))


class YieldParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Yield)

    def parse_statement(self, node: ast.Yield, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Yield, id_value, node.lineno, stmts, self.parsed_str(node))


class YieldFromParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.YieldFrom)

    def parse_statement(self, node: ast.YieldFrom, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.YieldFrom, id_value, node.lineno, stmts, self.parsed_str(node))


class CompareParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Compare)

    def parse_statement(self, node: ast.Compare, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Compare, id_value, node.lineno, stmts, self.parsed_str(node))


class CallParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Call)

    def parse_statement(self, node: ast.Call, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Call, id_value, node.lineno, stmts, self.parsed_str(node))


class FormattedValueParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.FormattedValue)

    def parse_statement(self, node: ast.FormattedValue, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.FormattedValue, id_value, node.lineno, stmts, self.parsed_str(node))


class JoinedStrParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.JoinedStr)

    def parse_statement(self, node: ast.JoinedStr, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.JoinedStr, id_value, node.lineno, stmts, self.parsed_str(node))


class SubscriptParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Subscript)

    def parse_statement(self, node: ast.Subscript, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Subscript, id_value, node.lineno, stmts, self.parsed_str(node))


class StarredParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Starred)

    def parse_statement(self, node: ast.Starred, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Starred, id_value, node.lineno, stmts, self.parsed_str(node))


class NameParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Name)

    def parse_statement(self, node: ast.Name, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Name, id_value, node.lineno, stmts, node.id)


class ListParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.List)

    def parse_statement(self, node: ast.List, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.List, id_value, node.lineno, stmts, self.parsed_str(node))


class TupleParser(StatementParser):
    def matches(self, node: ast.AST):
        return isinstance(node, ast.Tuple)

    def parse_statement(self, node: ast.Tuple, id_value: str) -> Statement:
        stmts = self.parse_fields(node, id_value)
        return Statement(StatementType.Tuple, id_value, node.lineno, stmts, self.parsed_str(node))
