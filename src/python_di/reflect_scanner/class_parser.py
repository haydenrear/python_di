import abc
import ast
import typing

import injector

from python_di.reflect_scanner.file_parser import ASTNodeParser
from python_di.reflect_scanner.function_parser import FnArgsParser, FnStatementParser
from python_di.reflect_scanner.module_graph_models import FileNode, NodeType, ClassFunctionFileNode


class ClassDefInnerParser(ASTNodeParser, abc.ABC):
    pass



class ClassFnParser(ClassDefInnerParser):

    @injector.inject
    def __init__(self, fn_args_parser: FnArgsParser,
                 fn_statement_parser: FnStatementParser):
        self.fn_statement_parser = fn_statement_parser
        self.fn_args_parser = fn_args_parser

    def parse(self, node: ast.FunctionDef, graph, source, parser=None, parent=None):
        assert parent is not None
        fn_node = ClassFunctionFileNode(parent.id_value, node.name)
        graph.add_node(fn_node)
        graph.add_edge(parent, fn_node)
        self.fn_args_parser.parse_args(fn_node, graph, node)
        self.fn_statement_parser.parse_stmts(fn_node, graph, node)


    def matches(self, node) -> bool:
        return isinstance(node, ast.FunctionDef)


class ClassDefParser(ASTNodeParser):

    @injector.inject
    def __init__(self, class_def_parser_parsers: typing.List[ClassDefInnerParser]):
        self.class_def_parser_parsers = class_def_parser_parsers

    def matches(self, node) -> bool:
        return isinstance(node, ast.ClassDef)

    def get_full_id(self, base: ast.Attribute | ast.Name):
        if isinstance(base, ast.Attribute):
            if isinstance(base.value, ast.Name):
                return f'{base.value.id}.{base.attr}'
            elif isinstance(base.value, ast.Attribute):
                return f'{self.get_full_id(base.value)}.{base.attr}'
        elif isinstance(base, ast.Name):
            return base.id


    def parse(self, node: ast.ClassDef, graph, source, parser=None, parent=None):
        assert parser is not None
        class_file_node = FileNode(NodeType.CLASS, node.name)
        graph.add_node(class_file_node)
        graph.add_edge(parent, class_file_node)
        for base in node.bases:
            if isinstance(base, ast.Name) or isinstance(base, ast.Attribute):
                base_id = self.get_full_id(base)
                base_name = base_id
                split_base_name = base_id.split('.')
                if len(split_base_name) > 1:
                    base_name = split_base_name[-1]

                base_node = FileNode(NodeType.BASE_CLASS, base_name)
                graph.add_node(base_node)
                if parent is not None:
                    graph.add_edge(parent, base_node)

                graph.add_edge(class_file_node, base_node)

                if len(split_base_name) > 1:
                    path_node = FileNode(NodeType.PATH, '.'.join(split_base_name[:-1]))
                    graph.add_node(path_node)
                    graph.add_edge(base_node, path_node)

        # TODO: add this to program parser
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                decorator_node = FileNode(NodeType.DECORATOR, decorator.func.id)
                graph.add_node(decorator_node)
                graph.add_edge(class_file_node, decorator_node)

        for child_node in ast.iter_child_nodes(node):
            is_looping = True
            for inner_parser in self.class_def_parser_parsers:
                if inner_parser.matches(child_node):
                    inner_parser.parse(child_node, graph, source, parser, class_file_node)
                    is_looping = False
                    break
            if not is_looping:
                continue
            else:
                parser.visit_node(child_node, source, class_file_node)

        return class_file_node
