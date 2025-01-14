import abc
import os
import typing

import injector
import networkx as nx

from python_di.reflect_scanner.scanner_properties import ScannerProperties
from python_util.io_utils.file_dirs import iterate_files_in_directories, get_base_path_of_current_file
from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.module_graph_models import FileNode, Import, ImportFrom, ProgramNode, NodeType
from python_di.reflect_scanner.file_parser import ASTNodeParser, FileParser
from python_di.reflect_scanner.program_parser_connector import ProgramParserConnectorArgs, ProgramParserConnector, \
    get_module
from python_di.reflection.resolve_src import ImportResolver, ImportType


class InclusionCriteria(abc.ABC):

    @abc.abstractmethod
    def do_include(self, import_string) -> bool:
        pass


class PythonSourceFileInclusionCriteria(InclusionCriteria):

    def do_include(self, x) -> bool:
        return '.py' in x and '.pyc' not in x


class SourceFileProvider(abc.ABC):
    """
    Once you have these connections within the files, using the FileParser, the program graph is created. The program
    graph creates unique ID's for the classes and functions using a combination of the id and the source file. The

    Iterates through to provide the files to be parsed.
    """

    @abc.abstractmethod
    def file_parser(self) -> typing.Iterator[str]:
        pass

    @abc.abstractmethod
    def base_source(self) -> list[str]:
        """
        :return: The directory that would import from. When creating the import it uses starts_with to remove this
        and then replaces slashes with dots to create imports.
        """
        pass


class ListBasedSourceFileProvider(SourceFileProvider):

    def __init__(self, sources: list[str]):
        self.source = sources
        self.walked = set([])

    def base_source(self) -> list[str]:
        return self.source

    def file_parser(self) -> typing.Iterator[str]:
        for directory_name in self.source:
            for subdir, dirs, files in os.walk(directory_name):
                for file in files:
                    if '.py' in file and '.pyc' not in file:
                        next_value = os.path.join(subdir, file)
                        if next_value not in self.walked:
                            yield next_value
                            self.walked.add(next_value)


class PropertyBasedSourceFileProvider(SourceFileProvider):
    """
    Once you have these connections within the files, using the FileParser, the program graph is created. The program
    graph creates unique ID's for the classes and functions using a combination of the id and the source file. The

    Iterates through to provide the files to be parsed.
    """

    @injector.inject
    def __init__(self,
                 scanner_properties: ScannerProperties,
                 filter_fn: PythonSourceFileInclusionCriteria):
        self.scanner_properties = scanner_properties
        self.filter_fn = filter_fn

    def file_parser(self) -> typing.Iterator[str]:
        yield from filter(self.filter_fn.do_include,
                          iterate_files_in_directories(get_base_path_of_current_file(self.scanner_properties.src_file,
                                                                                     self.scanner_properties.num_up)))

    def base_source(self) -> list[str]:
        return [get_base_path_of_current_file(self.scanner_properties.src_file,
                                              self.scanner_properties.num_up)]


class ProgramParser:

    @injector.inject
    def __init__(self,
                 ast_providers: typing.List[ASTNodeParser],
                 src_file_provider: SourceFileProvider,
                 module_inclusion_criteria: typing.List[InclusionCriteria],
                 program_graph_connectors: typing.List[ProgramParserConnector]):
        self.program_graph_connectors = program_graph_connectors
        self.module_inclusion_criteria = module_inclusion_criteria
        self.ast_providers = ast_providers
        self.src_file_provider = src_file_provider
        self.file_graphs: dict[str, FileParser] = {}
        self.external_file_graphs: dict[str, FileParser] = {}
        self.program_graph = nx.DiGraph()
        self.macro_expander = []

        for program_graph_connector in iter(sorted(self.program_graph_connectors,
                                                   key=lambda x: x.order() if x.order() is not None else 0)):
            program_graph_connector.program_graph = self.program_graph

    def set_source_file_provider(self, src_file_provider: SourceFileProvider):
        self.src_file_provider = src_file_provider

    def do_parse(self):
        """
        TODO: connect statements to delegate imports and then resolve delegate imports (see parse_statement_node in AggregateStatementParser)
        TODO: data structure to be able to add different types of indexes between different types of nodes, then search these indexes in different ways,
                expose it as MPC.
        TODO: 1. Write file as sub-graph with file as a sub-graph symbol on first pass - incrementally parse each file individually
              2. Write, on the second pass, the connections between the files - can write each file graph to cache
              3. Create program graph - resolve delegate imports from statements/other (language dependent) and connect file graphs to program graph incrementally
              4. Incrementally write the SCIP/LSIF index to the file
        :return:
        """
        sources = []
        for file in self.src_file_provider.file_parser():
            self.file_graphs[file] = FileParser(self.ast_providers)
            self.file_graphs[file].parse(file)
            sources.append(file)
        #   could write intermediary sub-graph with entry to metadata file - link below
        #   hierarchies of subgraphs obviously resolves adjacency list issue ... naive solution!!!

        LoggerFacade.info(f"Parsed program with the following sources:\n\n{sources}.")

        # Another pass through each of the file graphs, can be parallelized, to resolve and add undefined imports, which is
        # language dependent

        for file, file_graph in self.file_graphs.items():
            self.set_file_connections(file_graph.graph, self.program_graph, file)

        connector_args = ProgramParserConnectorArgs(self.file_graphs, self.external_file_graphs,
                                                    self.program_graph, self.src_file_provider.base_source())

        for program_graph in self.program_graph_connectors:
            program_graph.add_to_program_graph(connector_args)

    def add_dependency_graphs(self, resolved: str):
        if resolved not in self.file_graphs.keys() and os.path.exists(resolved) and os.path.isfile(resolved):
            self.external_file_graphs[resolved] = FileParser(self.ast_providers)
            self.external_file_graphs[resolved].parse(resolved)

    def set_file_connections(self, file_graph: nx.DiGraph,
                             program_graph: nx.DiGraph, source: str):
        """
        Add to the program graph the connections between the files based on the import
        :param file_graph:
        :param program_graph:
        :param source:
        :return:
        """
        program_graph.add_node(ProgramNode(NodeType.MODULE, source, source))
        edges_to_add = []
        for node in file_graph.nodes:
            if isinstance(node, Import | ImportFrom):
                import_type = determine_import_type(node)
                name = ', '.join(node.name)
                if not import_type:
                    LoggerFacade.error(f'Could not determine import type for node with name: {name}, module: '
                                       f'{node.module}.')
                else:
                    try:
                        if self.do_include_predicate(node):
                            resolved = ImportResolver.resolve_module_import(import_type, node, source)
                            self.assert_resolved_type(resolved)
                        else:
                            return None
                        if isinstance(resolved, typing.Collection):
                            for resolve in resolved:
                                self.assert_resolved_type(resolved)
                                self.add_to_dep(edges_to_add, program_graph, resolve, source)
                        else:
                            self.add_to_dep(edges_to_add, program_graph, resolved, source)
                    except Exception as e:
                        LoggerFacade.error(f"Failed to resolve import file: {e}")

        for edge in edges_to_add:
            file_graph.add_edge(edge[0], edge[1])

    def assert_resolved_type(self, resolved):
        assert (isinstance(resolved, typing.Collection | iter | str)), \
            f"Resolved was of " f"type: {type(resolved)}"

    def do_include_predicate(self, node):
        if isinstance(node, ImportFrom) and node.module is not None:
            import_from = (isinstance(node, ImportFrom) and self.any_do_include_criteria(node.module))
        else:
            import_from = False
        any_import_criteria = (any([self.any_do_include_criteria(name) for name in node.name])
                               or self.any_do_include_criteria(node.import_str))
        import_criteria = isinstance(node, Import | ImportFrom) and any_import_criteria
        return import_criteria or import_from

    def any_do_include_criteria(self, name):
        return any([criteria.do_include(name) for criteria in self.module_inclusion_criteria])

    def add_to_dep(self, edges_to_add, program_graph, resolved, source):
        resolved = ProgramNode(NodeType.MODULE, resolved, resolved)
        program_src = ProgramNode(NodeType.MODULE, source, source)
        program_graph.add_node(resolved)
        program_graph.add_edge(program_src, resolved)
        edges_to_add.append((FileNode(NodeType.MODULE, program_src.source_file),
                             FileNode(NodeType.MODULE, resolved.source_file)))
        self.add_dependency_graphs(resolved.source_file)


def is_node_in_module(module_name, mod_to_import):
    _, mod_dict = get_module(mod_to_import)
    return module_name in mod_dict.keys()


def determine_import_type(node: Import | ImportFrom):
    """
    Determines the type of import statement for a given AST node.

    Parameters:
        node (ast.Import or ast.ImportFrom): An AST node representing an import statement.

    Returns:
        str: A string representing the type of the import statement.
    """
    num_names = len(node.name) + len(node.as_name)
    if isinstance(node, Import):
        if num_names > 1:
            return ImportType.MultipleImport
        elif node.as_name is not None:
            return ImportType.AliasImport
        else:
            return ImportType.AbsoluteImport
    elif isinstance(node, ImportFrom):
        if node.level > 0:
            return ImportType.ExplicitRelativeImport
        elif num_names == 1 and node.name[0] == '*':
            return ImportType.WildcardImport
        elif num_names > 1 or (num_names == 1 and node.name[0] != '*'):
            return ImportType.SelectiveImport
    return "Unknown Import Type"
