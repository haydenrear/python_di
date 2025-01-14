import importlib
import typing

import injector
from injector import Binder

from python_di.inject.binder_utils import bind_multi_bind
from python_di.inject.context_builder.inject_ctx import inject_context_di
from python_di.inject.context_builder.injection_context import InjectionContext
from python_di.inject.injector_provider import InjectionContextInjector
from python_di.reflect_scanner.class_parser import ClassFnParser, ClassDefParser, ClassDefInnerParser
from python_di.reflect_scanner.file_parser import ASTNodeParser, FileParser
from python_di.reflect_scanner.function_parser import FunctionDefParser, FnStatementParser, FnArgsParser
from python_di.reflect_scanner.graph_scanner import DecoratorOfGraphScanner, SubclassesOfGraphScanner, \
    FunctionsOfGraphScanner, ModulesOfGraphScanner, ImportGraphScanner
from python_di.reflect_scanner.import_parser import ImportParser
from python_di.reflect_scanner.program_parser import ProgramParser, ModuleNameInclusionCriteria, \
    PropertyBasedSourceFileProvider, \
    InclusionCriteria, SourceFileProvider, SourceFileInclusionCriteria
from python_di.reflect_scanner.program_parser_connector import ClassParserConnector, FunctionArgsParserConnector, \
    ClassFunctionParserConnector, FunctionParserConnector, ProgramParserConnector, DecoratorParserConnector
from python_di.reflect_scanner.scanner_properties import ScannerProperties
from python_di.reflect_scanner.statements_parser import StatementParser, AggregateStatementParser
from python_di.reflect_scanner.type_introspector import TypeIntrospector, AttributeAstIntrospecter, TupleIntrospecter, \
    NameIntrospecter, DictClassDefParser, ListClassDefParser, OptionalClassDefParser, GenericClassDefParser, \
    SubscriptIntrospecter, ClassDefIntrospectParser, AggregateTypeIntrospecter, ListAstIntrospecter, \
    ConstantIntrospecter

T = typing.TypeVar("T")


class ReflectableCtx(injector.Module):
    parser_types = ['IfStatementParser', 'ForStatementParser',
                    'WhileStatementParser', 'AttributeParser', 'ValueParser', 'ConstantParser', 'FunctionDefParser',
                    'AsyncFunctionDefParser', 'ClassDefParser', 'ReturnParser', 'DeleteParser', 'AssignParser',
                    'AugAssignParser', 'AnnAssignParser', 'AsyncForParser', 'WithParser', 'AsyncWithParser',
                    'RaiseParser', 'TryParser', 'AssertParser', 'ImportParser', 'ImportFromParser', 'GlobalParser',
                    'NonLocalParser', 'ExprParser', 'PassParser', 'BreakParser', 'ContinueParser', 'BoolOpParser',
                    'BinOpParser', 'UnaryOpParser', 'LambdaParser', 'IfExpParser', 'DictParser', 'SetParser',
                    'ListCompParser', 'SetCompParser', 'DictCompParser', 'GeneratorExpParser', 'AwaitParser',
                    'YieldParser', 'YieldFromParser', 'CompareParser', 'CallParser', 'FormattedValueParser',
                    'JoinedStrParser', 'ConstantParser', 'AttributeParser', 'SubscriptParser', 'StarredParser',
                    'NameParser', 'ListParser', 'TupleParser']

    def configure(self, binder: Binder) -> None:
        self.bind_statement_parsers(binder)
        self.bind_introspecter(binder)
        self.bind_parser_connector(binder)
        self.bind_ast_node_parser(binder)
        self.bind_program_parser(binder)

    def bind_program_parser(self, binder: Binder):
        bind_multi_bind([ModuleNameInclusionCriteria], binder, typing.List[InclusionCriteria])
        binder.bind(SourceFileProvider, PropertyBasedSourceFileProvider, scope=injector.singleton)
        binder.bind(ProgramParser, ProgramParser, scope=injector.singleton)
        binder.bind(FileParser, FileParser, scope=injector.noscope)
        binder.bind(SourceFileInclusionCriteria, SourceFileInclusionCriteria, scope=injector.singleton)

        for graph_scanner in self._graph_scanner_tys():
            binder.bind(graph_scanner, graph_scanner, scope=injector.singleton)

        self.retrieve_bind_props(ScannerProperties)

    @staticmethod
    def _graph_scanner_tys():
        return [
            DecoratorOfGraphScanner,
            SubclassesOfGraphScanner,
            FunctionsOfGraphScanner,
            ModulesOfGraphScanner,
            ImportGraphScanner
        ]

    @inject_context_di()
    def retrieve_bind_props(self, to_register: typing.Type[T], ctx: typing.Optional[InjectionContextInjector]):
        if not ctx.contains_binding(to_register):
            ctx.register_config_properties(to_register, to_register.fallback)

    def bind_ast_node_parser(self, binder: Binder):
        binder.bind(FnArgsParser, FnArgsParser, scope=injector.singleton)
        binder.bind(FnStatementParser, FnStatementParser, scope=injector.singleton)
        bind_multi_bind([ClassFnParser], binder, typing.List[ClassDefInnerParser])
        bind_multi_bind([
            ClassDefParser,
            ImportParser,
            FunctionDefParser
        ], binder, typing.List[ASTNodeParser])

    def bind_parser_connector(self, binder: Binder):
        bind_multi_bind([
            ClassParserConnector,
            FunctionArgsParserConnector,
            ClassFunctionParserConnector,
            FunctionParserConnector,
            DecoratorParserConnector
        ], binder, typing.List[ProgramParserConnector])

    def bind_introspecter(self, binder):
        bind_multi_bind([
            AttributeAstIntrospecter,
            NameIntrospecter,
            TupleIntrospecter,
            SubscriptIntrospecter,
            ListAstIntrospecter,
            ConstantIntrospecter
        ], binder, typing.List[TypeIntrospector])
        bind_multi_bind([
            OptionalClassDefParser,
            ListClassDefParser,
            DictClassDefParser,
            GenericClassDefParser,
        ], binder, typing.List[ClassDefIntrospectParser])
        binder.bind(AggregateTypeIntrospecter, AggregateTypeIntrospecter, scope=injector.singleton)

    def bind_statement_parsers(self, binder):
        binder.bind(AttributeAstIntrospecter, AttributeAstIntrospecter, scope=injector.singleton)
        binder.bind(NameIntrospecter, NameIntrospecter, scope=injector.singleton)
        binder.bind(TupleIntrospecter, TupleIntrospecter, scope=injector.singleton)
        binder.bind(SubscriptIntrospecter, SubscriptIntrospecter, scope=injector.singleton)
        parser_types = {}
        for parser_type in ReflectableCtx.parser_types:
            mod = importlib.import_module('python_di.reflect_scanner.statements_parser')
            p_type = mod.__dict__[parser_type]
            parser_types[parser_type] = p_type
        bind_multi_bind([p for p in parser_types.values()], binder, typing.List[StatementParser])
        binder.bind(AggregateStatementParser, AggregateStatementParser, scope=injector.singleton)
