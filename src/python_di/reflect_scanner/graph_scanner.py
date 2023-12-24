import abc
import typing

import networkx as nx

from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.module_graph_models import Node, GraphType, FileNode, NodeType, ProgramNode


class GraphScannerArgs(abc.ABC):
    pass


GraphScannerArgsT = typing.TypeVar("GraphScannerArgsT", bound=GraphScannerArgs, covariant=True, )
NodeTypeT = typing.TypeVar("NodeTypeT", bound=Node, covariant=True)


class GraphScannerResult:
    def __init__(self, nodes: list[Node], source_nodes: list[Node] = None):
        self.source_nodes = source_nodes
        self.nodes = nodes


class ModulesOfGraphScannerResult:
    def __init__(self, nodes: typing.Collection[typing.Tuple[Node, Node]]):
        self.nodes = nodes


class ImportOfGraphScannerResult:
    def __init__(self, nodes: typing.Collection[typing.Tuple[Node, Node]]):
        self.nodes = nodes


class GraphScanner(abc.ABC, typing.Generic[GraphScannerArgsT]):
    """
    # TODO: conditioning on, for instance, text from a ticket - also [[AI Compilation]] -really just monitoring (bpf) and
       adding interface and plugin for compiling (probably C++ or Rust).
    There are two parts of the application that determine the way it runs. The code and the input data.

    The nodes will be parsed, signifying the type of node and the connections with the source code. The program graph
    will be created and then run through the recursive fish encoder to get an embedding of the program. Then, once
    this is provided, it will be inputted into a transformer-like architecture to predict the next step, and then
    the program is decoded back into the graph representation, at which time the cross entropy loss is taken, comparing
    the graph produced to the code of the next step.

    - ML Developer updates code, runs ML workflow
    - Code/data graph encoded along with data from the run
        - the graph includes code nodes and data nodes
        - the data nodes are associated with parts of the code, for example forward functions, optimizer, decorated.

            # Data Graph Representation
            -  You associate the data with, for instance the decorated function, and instead of having a temporal
               sequence for that data, you create an embedding of the data sequence and put it in one node of the graph.
               The data node is connected to the function node and the data nodes for that span, for example if it
               is a forward method then it does a layer norm, then it would be connected to the output of the layer
               norm also. However, it's only one node for all time steps.

            # Types of data
            - The data steps are first decomposed into their own graph, and embedded into one step. There are some k
              predefined types of data, for example validation loss, training loss, etc. New types of data can be added,
              but it requires additional training.
            - All data steps are embedded into a shared embedding size with it's own embedding encoder.
            - Each data type has it's own edge type. Edges between steps of sub-graph are of type index of node change or
              time step, edges within the sub-graph are either CODE or DATA. Same edge attributes as the edge between
              time step, in order to pull out information about how the node change related (adjacency matrix).
              DATA edges are of some k data types, such as validation, layer norm, etc.

            # Data Dimensions
            One of several ways:
                - The data types have predefined dimensions. The first iteration, for example, will include the embedding
                  size of 1280. All dimension types of data require an embedding to the shared dimension size
                - Time step transpose method with multihead attention embedding, with constant time step.
                - Have a database of embeddings, prototypes of data type all in same embedding size, and associated set
                  of linear layers for each prototype type. Need a way to use the previous data to train the new
                  linear layers. Assume that use class like EmbeddingSize to determine what data type, and only dimension
                  changes. Therefore, you have prototypes of EmbeddingSize from database. When creating new linear
                  layer, project it into same dim as cluster, and then loss is calculated as the cross entropy between
                  the output of the linear layer and the average of the top k closest embeddings from the data.

                  - This is the pre-training of the new linear layer, and then that linear layer is also trained as a
                    part of the network. Once it has been continued to be trained, it does forward to add data to the
                    database, and includes information for RAG?
                  - There are classifications of data types set as metadata for the architecture, for example gradients
                    for multi-modal feature fusion, text embedding, transformer layers, etc.
                  - Example - descriptive statistics for gradients, for example variance, learning rate, adaptive
                    learning rate.

    # Pretraining

    Pretraining is simple graph reconstruction, learning how to reconstruct the original graph from the embedded
    version, and then learning how to predict the next step from the previous step.

    # Architecture Training

    Architecture training is a reinforcement learning problem, using the change in the validation metrics as reward
    to make updates to the graph, or using Direct Preference.

    """

    @abc.abstractmethod
    def do_scan(self, graph_scanner_args: GraphScannerArgsT) -> GraphScannerResult:
        pass


class SubclassesOfGraphScannerArgs(GraphScannerArgs):
    def __init__(self, super_class: typing.Type, graph: nx.DiGraph, graph_type: GraphType):
        self.graph_type = graph_type
        self.graph = graph
        self.super_class = super_class


class DecoratorOfGraphScannerArgs(GraphScannerArgs):
    def __init__(self, decorator_id: str, graph: nx.DiGraph, graph_type: GraphType):
        self.decorator_id = decorator_id
        self.graph_type = graph_type
        self.graph = graph


class FunctionsOfGraphScannerArgs(GraphScannerArgs):
    def __init__(self, graph: nx.DiGraph, graph_type: GraphType):
        self.graph_type = graph_type
        self.graph = graph


class ModulesOfNodesArgs(GraphScannerArgs):
    def __init__(self, graph: nx.DiGraph, graph_type: GraphType,
                 nodes: list[Node]):
        self.nodes = nodes
        self.graph_type = graph_type
        self.graph = graph


class ImportFromNodesArgs(GraphScannerArgs):
    def __init__(self, graph: nx.DiGraph, graph_type: GraphType,
                 nodes: list[Node]):
        self.nodes = nodes
        self.graph_type = graph_type
        self.graph = graph


def matches(node: Node, graph_type: GraphType):
    if isinstance(node, FileNode):
        return graph_type == GraphType.File
    elif isinstance(node, ProgramNode):
        return graph_type == GraphType.Program


def _is_class_node(node: Node):
    is_class_type = node._node_type == NodeType.CLASS
    return is_class_type


def _is_import_node(node: Node):
    is_class_type = node._node_type == NodeType.IMPORT or node._node_type == NodeType.IMPORT_FROM
    return is_class_type


def retrieve_classes(file_parser: nx.DiGraph, graph_type: GraphType = GraphType.File) -> list[Node]:
    return_classes = []
    for node in file_parser.nodes:
        is_class_node = _is_class_node(node)
        matches_node_type = matches(node, graph_type)
        if is_class_node and matches_node_type:
            return_classes.append(node)
    return return_classes


def retrieve_functions(file_parser: nx.DiGraph, graph_type: GraphType = GraphType.File) -> list[Node]:
    returned_functions = list(filter(lambda node: node._node_type == NodeType.FUNCTION and matches(node, graph_type),
                                     file_parser.nodes))
    return returned_functions


def has_base_class(file_parser: nx.DiGraph, file_node: Node, base_class: typing.Type,
                   graph_type: GraphType = GraphType.File) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if to_._node_type == NodeType.BASE_CLASS and to_.id_value == base_class.__name__ and matches(to_, graph_type):
            if has_path_name(file_parser, to_, base_class.__module__):
                LoggerFacade.info(f"Found injector module during component scan: \n{file_node}\n.")
                return True


def retrieve_module(file_parser: nx.DiGraph, node: Node, graph_type: GraphType = GraphType.File):
    for from_, to_ in file_parser.out_edges(node):
        is_module = to_._node_type == NodeType.MODULE
        if is_module and matches(to_, graph_type):
            return to_


def retrieve_import(file_parser: nx.DiGraph, node: Node, graph_type: GraphType = GraphType.File):
    for from_, to_ in file_parser.out_edges(node):
        is_module = to_._node_type == NodeType.IMPORTED_DEPENDENCY or from_._node_type == NodeType.IMPORTED_DEPENDENCY
        if is_module and matches(to_, graph_type):
            return to_


def is_function(file_parser: nx.DiGraph, file_node: Node, graph_type: GraphType = GraphType.File) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if to_._node_type == NodeType.FUNCTION and matches(to_, graph_type):
            return True


def has_decorator_id(file_parser: nx.DiGraph, file_node: Node, decorator_id: str,
                     graph_type: GraphType = GraphType.File) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if to_._node_type == NodeType.DECORATOR and to_.id_value == decorator_id and matches(to_, graph_type):
            return True


def has_path_name(file_parser: nx.DiGraph, file_node: Node, path_name: str,
                  graph_type: GraphType = GraphType.File) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if to_._node_type == NodeType.PATH and to_.id_value == path_name and matches(to_, graph_type):
            return True


def retrieve_subclasses(file_parser: nx.DiGraph, superclass_name: typing.Type,
                        graph_type: GraphType = GraphType.File) -> list[Node]:
    return [
        c for c in retrieve_classes(file_parser, graph_type)
        if has_base_class(file_parser, c, superclass_name, graph_type) and matches(c, graph_type)
    ]


def retrieve_classes_decorated_by(file_parser: nx.DiGraph, decorator_id: str,
                                  graph_type: GraphType = GraphType.File) -> list[Node]:
    return [
        c for c in retrieve_classes(file_parser, graph_type)
        if has_decorator_id(file_parser, c, decorator_id, graph_type) and matches(c, graph_type)
    ]


def retrieve_functions_decorated_by(file_parser: nx.DiGraph, decorator_id: str,
                                    graph_type: GraphType = GraphType.File) -> list[Node]:
    return [
        c for c in retrieve_functions(file_parser, graph_type)
        if has_decorator_id(file_parser, c, decorator_id, graph_type) and matches(c, graph_type)
    ]


class SubclassesOfGraphScanner(GraphScanner[SubclassesOfGraphScannerArgs]):
    def do_scan(self, graph_scanner_args: SubclassesOfGraphScannerArgs) -> GraphScannerResult:
        out = retrieve_subclasses(graph_scanner_args.graph, graph_scanner_args.super_class,
                                  graph_scanner_args.graph_type)
        return GraphScannerResult(out)


class DecoratorOfGraphScanner(GraphScanner[DecoratorOfGraphScannerArgs]):
    def do_scan(self, graph_scanner_args: DecoratorOfGraphScannerArgs) -> GraphScannerResult:
        out = retrieve_classes_decorated_by(graph_scanner_args.graph, graph_scanner_args.decorator_id,
                                            graph_scanner_args.graph_type)
        fns = retrieve_functions_decorated_by(graph_scanner_args.graph, graph_scanner_args.decorator_id,
                                              graph_scanner_args.graph_type)
        out.extend(fns)
        return GraphScannerResult(out)


class FunctionsOfGraphScanner(GraphScanner[SubclassesOfGraphScannerArgs]):
    def do_scan(self, graph_scanner_args: FunctionsOfGraphScannerArgs) -> GraphScannerResult:
        out = retrieve_functions(graph_scanner_args.graph, graph_scanner_args.graph_type)
        return GraphScannerResult(out)


class ModulesOfGraphScanner(GraphScanner[SubclassesOfGraphScannerArgs]):
    def do_scan(self, graph_scanner_args: ModulesOfNodesArgs) -> ModulesOfGraphScannerResult:
        return ModulesOfGraphScannerResult([
            (retrieve_module(graph_scanner_args.graph, n, graph_scanner_args.graph_type), n)
            for n in graph_scanner_args.nodes
        ])


class ImportGraphScanner(GraphScanner[ImportFromNodesArgs]):
    def do_scan(self, graph_scanner_args: ImportFromNodesArgs) -> ImportOfGraphScannerResult:
        return ImportOfGraphScannerResult([
            (retrieve_import(graph_scanner_args.graph, n, graph_scanner_args.graph_type), n)
            for n in graph_scanner_args.nodes
        ])
