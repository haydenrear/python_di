import ast
import os.path

from python_util.logger.logger import LoggerFacade


def parse_ast_into_file(to_read_dir):
    if not os.path.exists(to_read_dir):
        LoggerFacade.error(f'Attempted to parse file that did not exist: {to_read_dir}.')
        return None
    with open(to_read_dir, 'r') as source:
        lines = source.read()
        lines = ''.join(lines)
        return ast.parse(lines)
