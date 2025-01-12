import ast
import os.path

from antlr4 import *
from antlr4.tree.Tree import ParseTreeWalker

from python_di.reflect_scanner.antlr_adapter.ast.antlr.java_lexer import JavaLexer
from python_di.reflect_scanner.antlr_adapter.ast.antlr.java_parser import JavaParser


def load_tokens_dict():
    tokens_dict = {}

    with open(os.path.join(os.path.dirname(__file__), 'antlr', 'JavaParser.tokens'), 'r') as t:
        for token in t.readlines():
            tokens_value = token.rsplit("=", 1)
            token_num = tokens_value[1].strip("\n")
            tokens_dict[int(token_num)] = tokens_value[0]

    return tokens_dict


# Function to parse Java code into AST representation
def load_ast(code):
    input_stream = InputStream(code)
    lexer = JavaLexer(input_stream)
    stream = CommonTokenStream(lexer)  # Custom class to extract tokens from JavaLexer.g4 (optional)
    parser = JavaParser(stream)
    tree = parser.compilationUnit()
    tokens_dict = load_tokens_dict()

    class ASTListener(ParseTreeWalker):
        def __init__(self):
            super().__init__()
            self.ast_tokens = []

        def visitTerminal(self, node):
            pass

        def visitErrorNode(self, node):
            print(f"Error parsing code: {node.getText()}")

        def enterEveryRule(self, ctx: ParserRuleContext):
            pass

        def exitEveryRule(self, ctx: ParserRuleContext):
            pass

    listener = ASTListener()
    listener.walk(listener, tree)
    return listener.ast_tokens


