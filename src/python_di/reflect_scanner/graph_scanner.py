import abc
import typing

import networkx as nx

from python_util.logger.logger import LoggerFacade
from python_di.reflect_scanner.module_graph_models import Node, GraphType, FileNode, NodeType


class GraphScannerArgs(abc.ABC):
    pass


GraphScannerArgsT = typing.TypeVar("GraphScannerArgsT", bound=GraphScannerArgs, covariant=True, )
NodeTypeT = typing.TypeVar("NodeTypeT", bound=Node, covariant=True)


class GraphScannerResult(typing.Generic[NodeTypeT]):
    def __init__(self, nodes: typing.Collection[NodeTypeT]):
        self.nodes = nodes


class GraphScanner(abc.ABC, typing.Generic[GraphScannerArgsT, NodeTypeT]):
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
    def do_scan(self, graph_scanner_args: GraphScannerArgsT) -> GraphScannerResult[NodeTypeT]:
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


def retrieve_classes(file_parser: nx.DiGraph) -> list[FileNode]:
    returned_classes = list(filter(lambda node: node.node_type == NodeType.CLASS, file_parser.nodes))
    return returned_classes


def has_base_class(file_parser: nx.DiGraph, file_node: FileNode, base_class: typing.Type) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if isinstance(to_, FileNode):
            if to_.node_type == NodeType.BASE_CLASS and to_.id_value == base_class.__name__:
                if has_path_name(file_parser, to_, base_class.__module__):
                    LoggerFacade.info(f"Found injector module during component scan: \n{file_node}\n.")
                    return True


def has_decorator_id(file_parser: nx.DiGraph, file_node: FileNode, decorator_id: str) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if isinstance(to_, FileNode):
            if to_.node_type == NodeType.DECORATOR and to_.id_value == decorator_id:
                return True


def has_path_name(file_parser: nx.DiGraph, file_node: FileNode, path_name: str) -> bool:
    for from_, to_ in file_parser.edges(file_node):
        if isinstance(to_, FileNode):
            if to_.node_type == NodeType.PATH and to_.id_value == path_name:
                return True


def retrieve_subclasses(file_parser: nx.DiGraph, superclass_name: typing.Type) -> list[FileNode]:
    return [
        c for c in retrieve_classes(file_parser)
        if has_base_class(file_parser, c, superclass_name)
    ]


def retrieve_classes_decorated_by(file_parser: nx.DiGraph, decorator_id: str) -> list[FileNode]:
    return [
        c for c in retrieve_classes(file_parser)
        if has_decorator_id(file_parser, c, decorator_id)
    ]


class SubclassesOfGraphScanner(GraphScanner[SubclassesOfGraphScannerArgs, NodeTypeT], typing.Generic[NodeTypeT]):
    def do_scan(self, graph_scanner_args: SubclassesOfGraphScannerArgs) -> GraphScannerResult[NodeTypeT]:
        if graph_scanner_args.graph_type == GraphType.Program:
            raise NotImplementedError("Have not implemented for FileNode")
        out = retrieve_subclasses(graph_scanner_args.graph, graph_scanner_args.super_class)
        return GraphScannerResult(out)


class DecoratorOfGraphScanner(GraphScanner[DecoratorOfGraphScannerArgs, NodeTypeT], typing.Generic[NodeTypeT]):
    def do_scan(self, graph_scanner_args: DecoratorOfGraphScannerArgs) -> GraphScannerResult[NodeTypeT]:
        if graph_scanner_args.graph_type == GraphType.Program:
            raise NotImplementedError("Have not implemented for FileNode")
        out = retrieve_classes_decorated_by(graph_scanner_args.graph, graph_scanner_args.decorator_id)
        return GraphScannerResult(out)
