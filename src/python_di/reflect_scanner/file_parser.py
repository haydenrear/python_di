import abc
import ast
import importlib
import typing

import injector
import networkx as nx
from abc import ABC, abstractmethod

from python_di.reflect_scanner.module_graph_models import NodeType, FileNode


# Define enums for GraphElement and NodeType
def retrieve_source_files(base_package: str):
    out = importlib.import_module(base_package)
    return out.__file__


class ASTNodeParser(ABC):

    @abstractmethod
    def parse(self, node, graph, source, parser=None, parent=None):
        pass

    @abc.abstractmethod
    def matches(self, node) -> bool:
        pass


class ContinueParseLibraryChecker(abc.ABC):
    @abc.abstractmethod
    def do_continue_parse(self, name: str):
        pass


class FileParser:
    """
    First, parse all classes, functions, and imports into a graph. For the imports, create an edge between each import
    and the source file. For the classes, add a link between each class and it's parent class. The classes and base
    classes are normalized by removing the path and adding a connection between it and the path.
    """

    @injector.inject
    def __init__(self, parsers: typing.List[ASTNodeParser]):
        self.parsers = parsers
        self.graph = nx.DiGraph()

    def visit_node(self, node, source_path, parent=None):
        if any([parser.matches(node) for parser in self.parsers]):
            for parser in self.parsers:
                if parser.matches(node):
                    parser.parse(node, self.graph, source_path, self, parent)
        else:
            for child_node in ast.iter_child_nodes(node):
                self.visit_node(child_node, source_path, parent)

    def parse(self, source_file_path) -> nx.DiGraph:
        with open(source_file_path, 'r') as source:
            lines = source.read()
            lines = ''.join(lines)
            tree = ast.parse(lines)
            mod_node = FileNode(NodeType.MODULE, source_file_path)
            self.graph.add_node(mod_node)

            for node in ast.iter_child_nodes(tree):
                self.visit_node(node, source_file_path, mod_node)

        return self.graph
