import unittest

import torch.nn
import torch

from torch import nn

from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.class_parser import ClassDefParser
from python_di.reflect_scanner.file_parser import FileParser
from python_di.reflect_scanner.function_parser import FunctionDefParser
from python_di.reflect_scanner.import_parser import ImportParser
from python_di.reflect_scanner.module_graph_models import Import, ImportFrom, FileNode, NodeType
from python_di.reflect_scanner.program_parser import ProgramParser, PropertyBasedSourceFileProvider
from python_di.reflect_scanner.program_parser_connector import get_import_containing_module


class TestOne(nn.Module):
    def __init__(self, one: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.one = one


class TestTwo(torch.nn.Module):
    def __init__(self, one: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.one = one


class AnotherOne(torch.ModuleDict):
    pass


def test_one():
    pass


class FileParserTest(unittest.TestCase):
    def test_file_parser(self):
        from python_di.inject.context_builder.injection_context import InjectionContext
        inject_ctx = InjectionContext()
        ctx = inject_ctx.initialize_env()
        file_parser = ctx.get_interface(FileParser)

        parsed = file_parser.parse(__file__)
        for graph in parsed.nodes:
            print(graph.id_value)

        out, src = get_import_containing_module('Module', file_parser.graph)
        assert src.endswith('torch/nn/__init__.py')
        torch_import = Import(['torch.nn'], [])
        edges = parsed.in_edges(torch_import)
        edges_list = list(iter(edges))
        assert len(edges_list) == 1
        edge_list_iter = iter(edges_list)
        file_node, import_value = next(edge_list_iter)

        assert file_node and import_value
        file_node: FileNode = file_node
        assert file_node.node_type == NodeType.MODULE
        assert file_node.id_value.endswith('test_file_parser.py')

        torch_count = 0
        for _, val in parsed.out_edges(file_node):
            if val.node_type == NodeType.BASE_CLASS and val.id_value == 'Module':
                torch_count += 1
                torch_out_edges = parsed.out_edges(val)
                parsed_out_edges = iter(torch_out_edges)
                _, path_one = next(parsed_out_edges)
                _, path_two = next(parsed_out_edges)
                self.assertRaises(StopIteration, lambda: next(parsed_out_edges))
                paths = [path_two, path_one]
                assert all([any([path.id_value == value for path in paths]) for value in [
                    'nn', 'torch.nn'
                ]])
            LoggerFacade.debug(f'Parsed value:\n{val}\n\n')

        assert torch_count == 1
