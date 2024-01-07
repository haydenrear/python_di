import abc
import importlib

import networkx as nx

from python_util.graph_util.graph_utils import get_node_cxns_out, get_node_cxns_in
from python_util.logger.logger import LoggerFacade
from python_util.ordered.ordering import Ordered
from python_di.reflect_scanner.file_parser import FileParser
from python_di.reflect_scanner.module_graph_models import FileNode, Import, ImportFrom, ProgramNode, NodeType, \
    ClassFunctionFileNode, ArgFileNode, TypeConnectionProgramNode, ClassFunctionProgramNode, DecoratorProgramNode, \
    DecoratorFileNode
from python_di.reflect_scanner.type_introspector import IntrospectedDef


class ProgramParserConnectorArgs:
    def __init__(self,
                 file_graphs: dict[str, FileParser],
                 external_file_graphs: dict[str, FileParser],
                 program_graph: nx.DiGraph,
                 sources: list[str]):
        self.sources = sources
        self.program_graph = program_graph
        self.external_file_graphs = external_file_graphs
        self.file_graphs = file_graphs


class ProgramParserConnector(Ordered, abc.ABC):

    def add_to_program_graph(self, connector_args: ProgramParserConnectorArgs):
        assert connector_args.program_graph is not None, "Must set program graph before adding to it."
        for source, file_graph in connector_args.file_graphs.items():
            for node in file_graph.graph.nodes:
                assert isinstance(node, FileNode)
                if not isinstance(node, Import | ImportFrom) and self.matches_node(node):
                    within_file = self.add_node_to_program_graph(connector_args, node, source)

                    self.add_sub_nodes_to_program_graph(node, file_graph.graph,
                                                        source, within_file,
                                                        connector_args)

    @classmethod
    def get_module_name(cls, id_value, source):
        for s in source:
            if id_value.startswith(s):
                id_value = id_value.replace(s, "").replace("/", ".")
                if len(id_value) != 0 and id_value[0] == ".":
                    id_value = id_value[1:]
                if id_value.endswith("py"):
                    id_value = id_value.replace(".py", "")
                return id_value

        return None


    def add_node_to_program_graph(self, connector_args, node, source):
        within_file = ProgramNode(node.node_type, source, node.id_value)
        source_node = ProgramNode(NodeType.MODULE, source, self.get_module_name(source, connector_args.sources))
        connector_args.program_graph.add_node(within_file)
        connector_args.program_graph.add_edge(within_file, source_node)
        return within_file

    @abc.abstractmethod
    def matches_node(self, node):
        pass

    @abc.abstractmethod
    def add_sub_nodes_to_program_graph(self, node, file_graph,
                                       source, class_program_node,
                                       connector_args: ProgramParserConnectorArgs):
        """
        Add the connections within the same file.
        :param node:
        :param file_graph:
        :param source:
        :param class_program_node:
        :param connector_args:
        :return:
        """
        pass

    @staticmethod
    def link_imported_to_program_graph(path_node: list[FileNode],
                                       base_program_node: ProgramNode,
                                       connector_args: ProgramParserConnectorArgs,
                                       file_graph: nx.DiGraph, source: str):
        """
        :param path_node:
        :param base_program_node:
        :param connector_args:
        :param file_graph:
        :param source:
        :return:
        """
        if path_node is not None and len(list(filter(lambda x: x, path_node))) != 0:
            for base_path_ in path_node:
                base_import = get_import_from_path(base_path_.id_value, file_graph.nodes)
                if base_import is None:
                    continue
                else:
                    # could never be a path from the same src file
                    mod_file, mod_dict = get_dict_file_from_module(base_import)
                    add_program_nodes_from_import(base_program_node, base_import, mod_file,
                                                  source, connector_args.program_graph)
        else:
            added = add_base_path_to_import(base_program_node, file_graph, source,
                                            connector_args)
            if added is None:
                LoggerFacade.warn(f"Could not find {base_program_node.id_value} in any file or external graph. "
                                  f"Could not add to ProgramGraph.")

    def link_sub_node_to_graph(self, file_node_linking, program_node_to_link, parent_program_node,
                               connector_args, file_graph, source):
        if program_node_to_link not in connector_args.program_graph.nodes:
            connector_args.program_graph.add_node(program_node_to_link)
        connector_args.program_graph.add_edge(parent_program_node, program_node_to_link)
        connector_args.program_graph.add_edge(program_node_to_link, parent_program_node)
        base_path: list[FileNode] = get_path(get_node_cxns_out(file_graph, file_node_linking))
        base_program_node = ProgramNode(file_node_linking.node_type, source, file_node_linking.id_value)
        LoggerFacade.debug(f'{file_node_linking.id_value} is base value.')
        if base_program_node not in connector_args.program_graph.nodes:
            connector_args.program_graph.add_node(base_program_node)
        self.link_imported_to_program_graph(base_path, base_program_node,
                                            connector_args, file_graph, source)


class ClassParserConnector(ProgramParserConnector):

    def matches_node(self, node):
        return node.node_type == NodeType.CLASS

    def order(self) -> int:
        return 0

    def add_sub_nodes_to_program_graph(self, node: FileNode, file_graph: nx.DiGraph,
                                       source: str, class_program_node: ProgramNode,
                                       connector_args: ProgramParserConnectorArgs):
        sub_nodes = get_node_cxns_out(file_graph, node)
        bases = get_bases(sub_nodes)
        for base in bases:
            assert isinstance(base, FileNode)
            base_program = ProgramNode(base.node_type, source, base.id_value)
            self.link_sub_node_to_graph(base, base_program, class_program_node,
                                        connector_args, file_graph, source)

    def add_node_to_program_graph(self, connector_args, node, source):
        within_file = ProgramNode(node.node_type, source, node.id_value)
        source_node = ProgramNode(NodeType.MODULE, source, self.get_module_name(source, connector_args.sources))
        connector_args.program_graph.add_node(source_node)
        connector_args.program_graph.add_node(within_file)
        connector_args.program_graph.add_edge(within_file, source_node)
        connector_args.program_graph.add_edge(source_node, within_file)
        return within_file


class FunctionArgsParserConnector(ProgramParserConnector):
    """
    Connects the function to the function args, and then connect the arg to the import or internal reference.
    """

    def matches_node(self, node):
        return node.node_type == NodeType.ARG

    def add_sub_nodes_to_program_graph(self, node: ArgFileNode, file_graph, source, class_program_node,
                                       connector_args: ProgramParserConnectorArgs):

        all_nodes_added = []
        for i in node.introspected:
            all_nodes_added.extend(
                self.create_add_recursive(i.get_introspected_tree(), file_graph, source, class_program_node,
                                          class_program_node, connector_args.program_graph))

        for node_added in all_nodes_added:
            self.link_sub_node_to_graph(node, node_added,
                                        class_program_node,
                                        connector_args, file_graph, source)

    def create_add_recursive(self, tree, file_graph, source, class_program_node, parent, program_graph,
                             added_nodes: list[TypeConnectionProgramNode] = None):
        if added_nodes is None:
            added_nodes = []
        if isinstance(tree, dict) and 'self_param' in tree.keys():
            next_i: IntrospectedDef = tree['self_param']
            next_ty_program_node = TypeConnectionProgramNode(source, source, next_i)
            program_graph.add_node(next_ty_program_node)
            program_graph.add_edge(parent, next_ty_program_node)
            added_nodes.append(next_ty_program_node)
            for key, val in tree.items():
                if key == 'self_param':
                    continue
                if isinstance(val, dict):
                    self.create_add_recursive(val, file_graph, source, class_program_node,
                                              next_i, program_graph, added_nodes)

        return added_nodes

    def order(self) -> int:
        return 1


def add_fn_statements(class_function_program_node, connector_args, file_graph, node, source):
    out_edges = get_node_cxns_out(file_graph, node)
    fn_statements = get_functions_stmts(out_edges)
    assert len(fn_statements) == 1
    fn_statements = fn_statements[0]
    fn_statement_program_node = ProgramNode(NodeType.STATEMENT, source, fn_statements.id_value)
    connector_args.program_graph.add_node(fn_statement_program_node)
    connector_args.program_graph.add_edge(class_function_program_node, fn_statement_program_node)


class DecoratorParserConnector(ProgramParserConnector):
    """
    Connects the function to the class.
    """

    def matches_node(self, node):
        return node.node_type == NodeType.DECORATOR and isinstance(node, DecoratorFileNode)

    def add_sub_nodes_to_program_graph(self, node: DecoratorFileNode, file_graph, source,
                                       decorated_program_node: DecoratorProgramNode,
                                       connector_args: ProgramParserConnectorArgs):
        LoggerFacade.debug(f'Getting in edges for {node.id_value}')
        in_edges = get_node_cxns_in(file_graph, node)
        for i in in_edges:
            LoggerFacade.debug(f'{i.id_value} is in edge')
        classes = get_classes(in_edges)
        for class_node in classes:
            class_program_node = ProgramNode(NodeType.CLASS, source, class_node.id_value)
            connector_args.program_graph.add_node(class_program_node)
            connector_args.program_graph.add_edge(class_program_node, decorated_program_node)
        functions = get_functions(in_edges)
        for function in functions:
            class_program_node = ProgramNode(NodeType.FUNCTION, source, function.id_value)
            connector_args.program_graph.add_node(class_program_node)
            connector_args.program_graph.add_edge(class_program_node, decorated_program_node)

    def order(self) -> int:
        return 2

    def add_node_to_program_graph(self, connector_args, node: DecoratorFileNode, source):
        within_file = DecoratorProgramNode(node.id_value, node.decorated_id, source, node.decorated_ty)
        source_node = ProgramNode(NodeType.MODULE, source, self.get_module_name(source, connector_args.sources))
        connector_args.program_graph.add_node(within_file)
        connector_args.program_graph.add_edge(within_file, source_node)
        return within_file


class ClassFunctionParserConnector(ProgramParserConnector):
    """
    Connects the function to the class.
    """

    def matches_node(self, node):
        return node.node_type == NodeType.FUNCTION and isinstance(node, ClassFunctionFileNode)

    def add_sub_nodes_to_program_graph(self, node: ClassFunctionFileNode, file_graph, source,
                                       class_function_program_node: ClassFunctionProgramNode,
                                       connector_args: ProgramParserConnectorArgs):
        LoggerFacade.debug(f'Getting in edges for {node.id_value}')
        in_edges = get_node_cxns_in(file_graph, node)
        for i in in_edges:
            LoggerFacade.debug(f'{i.id_value} is in edge')
        classes = get_classes(in_edges)
        assert len(classes) >= 1, "ClassFunctionFileNode must have an associated class in the FileGraph."
        for class_node in classes:
            class_program_node = ProgramNode(NodeType.CLASS, source, class_node.id_value)
            connector_args.program_graph.add_node(class_program_node)
            connector_args.program_graph.add_edge(class_program_node, class_function_program_node)

        add_fn_statements(class_function_program_node, connector_args, file_graph, node, source)

    def order(self) -> int:
        return 2

    def add_node_to_program_graph(self, connector_args, node: ClassFunctionFileNode, source):
        within_file = ClassFunctionProgramNode(node.class_id, source, node.id_value)
        source_node = ProgramNode(NodeType.MODULE, source, self.get_module_name(source, connector_args.sources))
        connector_args.program_graph.add_node(within_file)
        connector_args.program_graph.add_edge(within_file, source_node)
        return within_file


class FunctionParserConnector(ProgramParserConnector):

    def matches_node(self, node):
        return node.node_type == NodeType.FUNCTION and not isinstance(node, ClassFunctionFileNode)

    def add_sub_nodes_to_program_graph(self, node, file_graph, source, function_program_node,
                                       connector_args: ProgramParserConnectorArgs):
        add_fn_statements(function_program_node, connector_args, file_graph, node, source)

    def order(self) -> int:
        return 0


def get_import_containing_module(module_name: str, graph_to_search) -> (Import | ImportFrom, object):
    for node in graph_to_search.nodes:
        mod_file, mod_dict = get_dict_file_from_module(node)
        if mod_dict is not None:
            if module_name in mod_dict.keys():
                return node, mod_file
            elif len(node.as_name) >= 1 and module_name in node.as_name:
                assert node.name[0] in mod_dict.keys()
                return node, mod_file

    return None, None


def get_dict_file_from_module(node: Import | ImportFrom):
    if isinstance(node, Import):
        for mod in filter(lambda x: x, node.name):
            mod_file, mod_dict = get_module(mod)
            if mod_file is not None:
                return mod_file, mod_dict
    elif isinstance(node, ImportFrom):
        if node.module is not None:
            return get_module(node.module)
        elif len(node.name) >= 1:
            for mod in node.name:
                mod_file, mod_dict = get_module(mod)
                if mod_file is not None:
                    return node, mod_file

    return None, None


def get_module(mod):
    try:
        LoggerFacade.debug(f"Importing {mod}.")
        imported_module = importlib.import_module(mod)
        if hasattr(imported_module, '__file__') and hasattr(imported_module, '__dict__'):
            return imported_module.__file__, imported_module.__dict__
        else:
            return None, None
    except Exception as e:
        LoggerFacade.debug(f"Could not import module: {mod}, with error: {e}.")
        return None, None


def get_path(nodes: list):
    return [node for node in nodes if node.node_type == NodeType.PATH]


def get_bases(nodes: list):
    return [node for node in nodes
            if node.node_type == NodeType.BASE_CLASS]


def get_classes(nodes: list):
    return [node for node in nodes
            if node.node_type == NodeType.CLASS]


def get_decorators(nodes: list):
    return [node for node in nodes
            if node.node_type == NodeType.DECORATOR]


def get_functions(nodes: list):
    return [node for node in nodes
            if node.node_type == NodeType.FUNCTION]


def get_functions_stmts(nodes: list):
    return [node for node in nodes
            if node.node_type == NodeType.STATEMENT]


def get_import_from_path(path: str, nodes):
    for node in nodes:
        if isinstance(node, Import | ImportFrom):
            if isinstance(node, ImportFrom) and path == node.module:
                return node
            if path in node.as_name or path in node.name:
                return node


def add_program_nodes_from_import(base, found_import_mod, mod_src_file, source, program_graph):
    # add the imported dependency to the graph
    import_node = ProgramNode(NodeType.IMPORTED_DEPENDENCY, source, found_import_mod.id_value)
    program_graph.add_node(import_node)
    # add connection between base class representation and import for base class
    program_graph.add_edge(base, import_node)

    # add the representation of the src file for the import
    mod_src = ProgramNode(NodeType.MODULE, mod_src_file, found_import_mod.id_value)
    program_graph.add_node(mod_src)
    # add the connection between the import for class and the src file imported from
    program_graph.add_edge(import_node, mod_src)
    return found_import_mod


def add_program_nodes_same_src(base, found_in_mod, source, program_graph,
                               node_type: NodeType = NodeType.CLASS):
    """
    Add connection between the node base and the import module node found by adding the Import module to the
    ProgramGraph, the base node, and a node that connects the two, SAME_SRC_DEPENDENCY node.
    :param base:
    :param found_in_mod:
    :param source:
    :param program_graph:
    :param node_type:
    :return:
    """
    # add the representation for same src dependency
    same_src_node = ProgramNode(NodeType.SAME_SRC_DEPENDENCY, source, found_in_mod.id_value)
    found_in_mod = ProgramNode(node_type, source, found_in_mod.id_value)

    program_graph.add_node(found_in_mod)
    program_graph.add_node(same_src_node)
    # add the connection between the base class representation and the same src dependency
    program_graph.add_edge(base, same_src_node)
    program_graph.add_edge(found_in_mod, same_src_node)
    return found_in_mod


def add_from_import(base, file_graph, source, program_graph, node_type: NodeType = NodeType.CLASS):
    found_mod, mod_src_file = get_import_containing_module(base.id_value, file_graph)
    if not found_mod or not mod_src_file:
        # handle case where dependency is in same src file because there is no import to get the src file from.
        for node in file_graph.nodes:
            assert isinstance(node, FileNode)
            if node.node_type == node_type and node.id_value == base.id_value:
                return add_program_nodes_same_src(base, node, source, program_graph, node_type)
        return None

    return add_program_nodes_from_import(base, found_mod, mod_src_file, source, program_graph)


def add_base_path_to_import(base, file_graph, source, connector_args: ProgramParserConnectorArgs):
    """
    Add the base node to the graph by obtaining it's source file and the relationship between it and the
    source node, source file.
    Class -> Base
    Base -> ImportedDependency
    Import -> Src
    OR
    Class -> Base
    Base -> SameFileDependency
    SameFileDependency -> SameFile
    :param connector_args:
    :param base:
    :param file_graph:
    :param source:
    :return:
    """
    found = add_from_import(base, file_graph, source, connector_args.program_graph)
    if found is not None:
        return found
    else:
        for key, graph in connector_args.file_graphs.items():
            found = add_from_import(base, graph.graph, source,
                                    connector_args.program_graph)
            if found is not None:
                return found

        for key, external_graph in connector_args.external_file_graphs.items():
            found = add_from_import(base, external_graph.graph, source,
                                    connector_args.program_graph)
            if found is not None:
                return found
