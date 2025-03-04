import ast
import os.path
import typing
from queue import Queue

from antlr4 import *
from antlr4.tree.Tree import ParseTreeWalker, TerminalNodeImpl

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
            self.ast_tokens: list[ast.AST] = []
            # to pop from
            self.prevs: list[ast.AST] = []
            self.curr: typing.Optional[ast.AST] = None

        def visitTerminal(self, node: TerminalNodeImpl):
            p = node.parentCtx
            pass

        def visitErrorNode(self, node):
            print(f"Error parsing code: {node.getText()}")

        def enterEveryRule(self, ctx: ParserRuleContext):
            if isinstance(ctx, JavaParser.PackageDeclarationContext):
                pass
            if isinstance(ctx, JavaParser.TypeDeclarationContext):
                pass
            if isinstance(ctx, JavaParser.ClassOrInterfaceModifierContext):
                pass
            if isinstance(ctx, JavaParser.ClassOrInterfaceTypeContext):
                pass

        def exitEveryRule(self, ctx: ParserRuleContext):
            if isinstance(ctx, JavaParser.PackageDeclarationContext):
                pass
            if isinstance(ctx, JavaParser.TypeDeclarationContext):
                pass
            if isinstance(ctx, JavaParser.ClassOrInterfaceModifierContext):
                pass
            if isinstance(ctx, JavaParser.ClassOrInterfaceTypeContext):
                pass

    listener = ASTListener()
    listener.walk(listener, tree)
    return listener.ast_tokens


