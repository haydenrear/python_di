import importlib
import logging
import os
import unittest

import networkx as nx

from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.inject.context_builder.injection_context import InjectionContext
from python_util.logger.logger import LoggerFacade
from python_util.logger.log_level import LogLevel
from python_di.reflect_scanner.module_graph_models import NodeType, ProgramNode
from python_di.reflect_scanner.program_parser import ProgramParser
from python_di.reflect_scanner.scanner_properties import ScannerProperties


@enable_configuration_properties(config_props=[ScannerProperties])
class ModuleScannerTest(unittest.TestCase):

    def setUp(self) -> None:
        from python_di.inject.context_builder.injection_context import InjectionContext
        inject_ctx = InjectionContext()
        ctx = inject_ctx.initialize_env()
        self.scanner_props: ScannerProperties = ctx.get_interface(ScannerProperties)
        assert self.scanner_props.num_up == 0

        self.parser: ProgramParser = ctx.get_interface(ProgramParser)
        self.parser.do_parse()

        for n in self.parser.program_graph.nodes:
            print(n)
        assert self.parser.file_graphs
        assert self.parser.program_graph
        self.torch_file = 'lib/python3.11/site-packages/torch/nn/__init__.py'

    def test_module_import(self):
        imported = importlib.import_module('torch.nn')
        assert 'Module' in imported.__dict__.keys()
        assert imported.__file__.endswith(self.torch_file)

    def test_digraph(self):
        digraph = nx.DiGraph()
        digraph.add_node('one')
        digraph.add_node('two')
        digraph.add_edge('one', 'two')

        nodes = digraph.nodes('one')
        assert len(nodes) == 2

    def test_contains_external_files(self):
        assert self.contains_node_with_filename(
            self.parser, self.torch_file)
        assert self.contains_node_with_filename(
            self.parser, 'lib/python3.11/site-packages/torch')

        self.class_base_dependency_same_file(self.parser)

    def test_import(self):
        found = self.get_node_with_node_type(self.parser, "FoundationTokenizerImport", NodeType.CLASS)
        found_edges = self.get_all_edges_for_node(found, self.parser)
        is_valid = False
        for (to, from_e) in found_edges:
            if isinstance(from_e, ProgramNode):
                if from_e.node_type == NodeType.BASE_CLASS:
                    assert from_e.id_value == "FoundationTokenizer"
                    for (to_t, from_t) in self.get_all_edges_for_node(from_e, self.parser):
                        if isinstance(from_t, ProgramNode):
                            if from_t.node_type == NodeType.IMPORTED_DEPENDENCY:
                                is_valid = True

        assert is_valid



    def class_base_dependency_same_file(self, program_parser):
        assert self.contains_node(self.parser, 'FoundationTokenizerFactory')
        # find huggingface tokenizer factory
        node = self.get_node_with_node_type(program_parser, 'HuggingFaceTokenizerConfigFactory', NodeType.CLASS)
        assert node is not None
        # huggingface tokenizer factory has base class FoundationTokenizerFactory
        config_factory = self.get_in_edge_named(node, program_parser, 'FoundationTokenizerFactory',
                                                NodeType.BASE_CLASS)

        config_factory = self.get_node_with_node_type(program_parser, config_factory.id_value, config_factory.node_type)
        assert config_factory is not None
        # FoundationTokenizerFactory is from that same module.
        LogLevel.set_log_level(logging.DEBUG)
        self.contains_node(program_parser, 'FoundationTokenizerFactory')
        node_type = self.get_node_with_node_type(program_parser, config_factory.id_value, NodeType.SAME_SRC_DEPENDENCY)
        LoggerFacade.debug("Found same src node: ")
        self.log_program_node(node_type)
        assert node_type is not None

    def get_all_edges_for_node(self, node, program_parser):
        return program_parser.program_graph.edges(node)

    def get_in_edge_named(self, node, program_parser, name, node_type):
        edges = program_parser.program_graph.out_edges(node)
        for in_edge, out_edge in edges:
            self.log_program_node(in_edge)
            self.log_program_node(out_edge)
            if out_edge.id_value == name and out_edge.node_type == node_type:
                return out_edge

    def log_program_node(self, node: ProgramNode):
        LoggerFacade.info(f'Found program node {node.id_value} with type {node.node_type} from {node.source_file}')


    def get_node_with_node_type(self, program_parser, name, node_type):
        for node in program_parser.program_graph.nodes:
            value_name = node.id_value == name
            node_node_type = node.node_type
            if value_name and node_node_type == node_type:
                LoggerFacade.debug(f'Found node: {name}: {node.id_value}, {node.source_file}.')
                return node

    def contains_node_with_filename(self, program_parser, parser_name):
        has_node = False
        for node in program_parser.program_graph.nodes:
            if parser_name in node.source_file:
                has_node = True
        return has_node

    def contains_node(self, program_parser, name):
        has_node = False
        for node in program_parser.program_graph.nodes:
            if node.id_value == name:
                LoggerFacade.debug(f'Found node: {name}: {node.id_value}, {node.source_file}, {node.node_type}.')
                for from_edge, to_edge in program_parser.program_graph.edges(node):
                    LoggerFacade.debug(f'Found from node: {name}: {from_edge.id_value}, {from_edge.source_file}, {from_edge.node_type}.')
                    LoggerFacade.debug(f'Found from node: {name}: {to_edge.id_value}, {to_edge.source_file}, {to_edge.node_type}.')

                has_node = True
        return has_node
