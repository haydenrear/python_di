import tokenize
from io import BytesIO

from python_di.reflect_scanner.module_graph_models import ProgramNode, NodeType


def extract_source(node, source_code):
    """
    Extract the source code for a specific AST node.

    :param node: The AST node.
    :param source_code: The source code from which the node was parsed.
    :return: Source code associated with the node.
    """
    if isinstance(node, ProgramNode):
        if node.node_type == NodeType.MODULE:
            with open(node.source_file, 'r') as source_code:
                return source_code.readlines()
        elif node.node_type == NodeType.IMPORT or node.node_type == NodeType.IMPORT_FROM:
            return node.id_value

    # Tokenize the source code and build a mapping between start/end positions and the tokens.
    tokens = list(tokenize.tokenize(BytesIO(source_code.encode('utf-8')).readline))
    token_map = {(token.start, token.end): token.string for token in tokens}

    # Find the start and end position for the node.
    start_pos = (node.lineno, node.col_offset)
    if hasattr(node, 'end_lineno') and hasattr(node, 'end_col_offset'):
        # Use the end position of the node (available in Python 3.8+).
        end_pos = (node.end_lineno, node.end_col_offset)
    else:
        # If the end position isn't available, use the start position of the next node.
        end_pos = tokens[min(i + 1 for i, tok in enumerate(tokens) if tok.start == start_pos)].start

    # Extract and concatenate tokens between the start and end position.
    code_parts = [token_map[pos] for pos in sorted(token_map.keys()) if start_pos <= pos < end_pos]
    return ''.join(code_parts)
