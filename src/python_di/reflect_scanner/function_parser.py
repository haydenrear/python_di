import abc
import ast
import typing
import networkx as nx

from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.module_graph_models import FileNode, NodeType, ArgFileNode, IntrospectedPathNode
from python_di.reflect_scanner.file_parser import ASTNodeParser
import injector

from python_di.reflect_scanner.statements_parser import AggregateStatementParser
from python_di.reflect_scanner.type_introspector import AggregateTypeIntrospecter, IntrospectedDef



class FnArgsParser:

    @injector.inject
    def __init__(self, type_introspecter: AggregateTypeIntrospecter):
        self.type_introspecter = type_introspecter

    def parse_args(self, fn_node: FileNode, graph: nx.DiGraph, node: ast.FunctionDef):
        for arg in node.args.args:
            if isinstance(arg, ast.arg):
                if arg.annotation is not None:
                    introspected = self.type_introspecter.introspect_type(arg.annotation)
                    LoggerFacade.debug(f'{introspected} was introspected for {arg.annotation}.')
                    if introspected is not None:
                        path_nodes = self.add_introspected_path_nodes_to_graph(graph, introspected)

                        for i in introspected:
                            i.remove_path()

                        arg_node = ArgFileNode(arg.arg, introspected)
                        graph.add_node(arg_node)
                        graph.add_edge(fn_node, arg_node)

                        for introspected_path_node in path_nodes:
                            graph.add_edge(arg_node, introspected_path_node)
                    else:
                        arg_node = ArgFileNode(str(arg.annotation), [])
                        graph.add_node(arg_node)
                        graph.add_edge(fn_node, arg_node)

                else:
                    arg_node = ArgFileNode(arg.arg, [])
                    graph.add_node(arg_node)
                    graph.add_edge(fn_node, arg_node)


    @staticmethod
    def add_introspected_path_nodes_to_graph(graph, introspected):
        path_nodes = []
        for introspect in introspected:
            introspect: IntrospectedDef = introspect
            for class_dep in introspect.get_class_deps():
                path_i = class_dep.split('.')
                if len(path_i) > 1:
                    path = path_i[:-1]
                    path_node = IntrospectedPathNode('.'.join(path), introspect)
                    graph.add_node(path_node)
                    path_nodes.append(path_node)

        return path_nodes

    def matches(self, node) -> bool:
        return isinstance(node, ast.FunctionDef)


class FnStatementParser:
    @injector.inject
    def __init__(self, stmt_parser: AggregateStatementParser):
        self.stmt_parser = stmt_parser

    def parse_stmts(self, fn_node: FileNode, graph: nx.DiGraph, node: ast.FunctionDef):
        statement_node = self.stmt_parser.parse_statement_node(node.body, fn_node.id_value)
        graph.add_node(statement_node)
        graph.add_edge(fn_node, statement_node)



class FunctionDefParser(ASTNodeParser):

    @injector.inject
    def __init__(self,
                 fn_args_parser: FnArgsParser,
                 statement_parser: FnStatementParser):
        self.statement_parser = statement_parser
        self.fn_args_parser = fn_args_parser

    def parse(self, node: ast.FunctionDef,
              graph, source, parser=None, parent=None):
        fn_node = FileNode(NodeType.FUNCTION, node.name)
        graph.add_node(fn_node)
        if parent is not None:
            graph.add_edge(parent, fn_node)
        self.fn_args_parser.parse_args(fn_node, graph, node)
        self.statement_parser.parse_stmts(fn_node, graph, node)


    def matches(self, node) -> bool:
        return isinstance(node, ast.FunctionDef)
