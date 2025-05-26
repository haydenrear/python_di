import ast
import os
import typing
from enum import Enum, auto
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker

from python_di.reflect_scanner.antlr_adapter.ast.antlr.java_lexer import JavaLexer
from python_di.reflect_scanner.antlr_adapter.ast.antlr.java_parser import JavaParser
from python_di.reflect_scanner.antlr_adapter.ast.antlr.java_parser_listener import JavaParserListener
from python_util.logger.logger import LoggerFacade


class Language(Enum):
    JAVA = auto()
    PYTHON = auto()
    UNKNOWN = auto()


class LanguageDetector:
    """Detects the language of a file based on its extension."""
    
    EXTENSION_MAP = {
        '.java': Language.JAVA,
        '.py': Language.PYTHON,
    }
    
    @staticmethod
    def detect_language(file_path: str) -> Language:
        """Detect the language of a file based on its extension."""
        _, ext = os.path.splitext(file_path)
        return LanguageDetector.EXTENSION_MAP.get(ext.lower(), Language.UNKNOWN)


class AntlrToAstConverter:
    """Base class for converting ANTLR parse trees to Python AST."""
    
    def convert(self, file_path: str) -> list[ast.AST]:
        """Convert a file to a list of Python AST nodes."""
        raise NotImplementedError("Subclasses must implement this method")


class JavaAntlrToAstListener(JavaParserListener):
    """Listens to ANTLR parse tree events for Java and builds a Python AST."""
    
    def __init__(self):
        super().__init__()
        self.ast_nodes = []
        self.imports = []
        self.package = None
        self.current_class = None
        
    def enterPackageDeclaration(self, ctx):
        # Extract package name from context
        if ctx.qualifiedName():
            package_parts = []
            # Walk through the identifier tokens to build the package name
            for id_ctx in ctx.qualifiedName().identifier():
                package_parts.append(id_ctx.getText())
            self.package = ".".join(package_parts)
            
    def enterImportDeclaration(self, ctx):
        # Extract import information
        is_static = ctx.STATIC() is not None
        is_wildcard = ctx.MUL() is not None
        qualified_name_parts = []
        
        if ctx.qualifiedName():
            for id_ctx in ctx.qualifiedName().identifier():
                qualified_name_parts.append(id_ctx.getText())
        
        qualified_name = ".".join(qualified_name_parts)
        
        # Create an ImportFrom node for Java imports
        import_node = ast.ImportFrom(
            module=qualified_name,
            names=[ast.alias(name='*' if is_wildcard else qualified_name.split('.')[-1], asname=None)],
            level=0
        )
        self.imports.append(import_node)
        
    def enterClassDeclaration(self, ctx):
        # Create a ClassDef node for Java class
        class_name = ctx.identifier().getText()
        
        # Handle inheritance
        bases = []
        if ctx.EXTENDS():
            # Add the extended class as a base
            if ctx.typeType():
                base_type = ctx.typeType().getText()
                bases.append(ast.Name(id=base_type, ctx=ast.Load()))
        
        # Handle interfaces
        if ctx.IMPLEMENTS():
            if ctx.typeList():
                for type_ctx in ctx.typeList().typeType():
                    base_type = type_ctx.getText()
                    bases.append(ast.Name(id=base_type, ctx=ast.Load()))
        
        # Create the class node
        class_node = ast.ClassDef(
            name=class_name,
            bases=bases,
            keywords=[],
            body=[],  # Will be filled by method declarations
            decorator_list=[]
        )
        
        self.current_class = class_node
        self.ast_nodes.append(class_node)
        
    def exitClassDeclaration(self, ctx):
        self.current_class = None
        
    def enterMethodDeclaration(self, ctx):
        if self.current_class is None:
            return
            
        # Extract method name
        method_name = ctx.identifier().getText()
        
        # Extract return type
        return_type = None
        if ctx.typeTypeOrVoid():
            return_type = ctx.typeTypeOrVoid().getText()
            
        # Extract parameters
        params = []
        if ctx.formalParameters() and ctx.formalParameters().formalParameterList():
            param_list = ctx.formalParameters().formalParameterList()
            for param_ctx in param_list.formalParameter():
                param_name = param_ctx.variableDeclaratorId().identifier().getText()
                params.append(ast.arg(arg=param_name, annotation=None))
        
        # Create a function definition node
        func_node = ast.FunctionDef(
            name=method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=params,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
                vararg=None,
                kwarg=None
            ),
            body=[ast.Pass()],  # Placeholder
            decorator_list=[],
            returns=ast.Name(id=return_type, ctx=ast.Load()) if return_type else None
        )
        
        # Add to current class
        self.current_class.body.append(func_node)


class JavaAntlrToAstConverter(AntlrToAstConverter):
    """Converts Java files to Python AST using ANTLR."""
    
    def convert(self, file_path: str) -> list[ast.AST]:
        try:
            # Read the file
            with open(file_path, 'r') as file:
                input_stream = InputStream(file.read())
            
            # Create lexer and parser
            lexer = JavaLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = JavaParser(token_stream)
            
            # Parse the compilation unit (root of Java file)
            tree = parser.compilationUnit()
            
            # Create listener and walk the parse tree
            listener = JavaAntlrToAstListener()
            walker = ParseTreeWalker()
            walker.walk(listener, tree)
            
            return listener.ast_nodes
            
        except Exception as e:
            LoggerFacade.error(f"Failed to parse Java file {file_path}: {e}")
            return []


def from_antlr(file_path: str) -> list[ast.AST]:
    """
    Convert an ANTLR-parseable file to Python AST nodes.
    
    Args:
        file_path: Path to the file to parse
        
    Returns:
        A list of Python AST nodes representing the file's contents
    """
    # Detect the language
    language = LanguageDetector.detect_language(file_path)
    
    # Use the appropriate converter
    if language == Language.JAVA:
        converter = JavaAntlrToAstConverter()
        return converter.convert(file_path)
    elif language == Language.PYTHON:
        # For Python files, we can use the built-in ast module
        try:
            with open(file_path, 'r') as file:
                tree = ast.parse(file.read())
                return [tree]
        except Exception as e:
            LoggerFacade.error(f"Failed to parse Python file {file_path}: {e}")
            return []
    else:
        LoggerFacade.warn(f"Unsupported language for file {file_path}")
        return []
