import importlib
import typing

import injector
from injector import Binder

from python_di.inject.inject_context_di import inject_context_di
from python_di.inject.injector_provider import InjectionContext, T
from python_di.reflect_scanner.class_parser import ClassFnParser, ClassDefParser, ClassDefInnerParser
from python_di.reflect_scanner.file_parser import ASTNodeParser, FileParser
from python_di.reflect_scanner.function_parser import FunctionDefParser, FnStatementParser, FnArgsParser
from python_di.reflect_scanner.graph_scanner import DecoratorOfGraphScanner, SubclassesOfGraphScanner
from python_di.reflect_scanner.import_parser import ImportParser
from python_di.reflect_scanner.program_parser import ProgramParser, ModuleNameInclusionCriteria, SourceFileProvider, \
    InclusionCriteria
from python_di.reflect_scanner.program_parser_connector import ClassParserConnector, FunctionArgsParserConnector, \
    ClassFunctionParserConnector, FunctionParserConnector, ProgramParserConnector
from python_di.reflect_scanner.statements_parser import StatementParser, AggregateStatementParser
from python_di.reflect_scanner.type_introspector import TypeIntrospector, AttributeAstIntrospecter, TupleIntrospecter, \
    NameIntrospecter, DictClassDefParser, ListClassDefParser, OptionalClassDefParser, GenericClassDefParser, \
    SubscriptIntrospecter, ClassDefIntrospectParser, AggregateTypeIntrospecter, ListAstIntrospecter, \
    ConstantIntrospecter


@inject_context_di()
def bind_multi_bind(multi_bind: typing.List[typing.Type[T]], binder, multi_bind_name,
                    ctx: typing.Optional[InjectionContext] = None):
    for to_bind in multi_bind:
        if to_bind not in binder._bindings.keys():
            binder.bind(to_bind, to_bind, scope=injector.singleton)
    binder.multibind(multi_bind_name, lambda: [
        ctx.get_interface(to_bind, scope=injector.singleton) for to_bind in multi_bind
    ], scope=injector.singleton)


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

    def bind_config_props(self, binder, to_bind):
        for t in to_bind:
            prop = InjectionContext.get_interface(t)
            binder.bind(t, prop, scope=injector.singleton)

    def bind_program_parser(self, binder: Binder):
        bind_multi_bind([ModuleNameInclusionCriteria], binder, typing.List[InclusionCriteria])
        binder.bind(SourceFileProvider, SourceFileProvider, scope=injector.singleton)
        binder.bind(ProgramParser, ProgramParser, scope=injector.singleton)
        binder.bind(FileParser, FileParser, scope=injector.noscope)
        binder.bind(DecoratorOfGraphScanner, DecoratorOfGraphScanner, scope=injector.singleton)
        binder.bind(SubclassesOfGraphScanner, SubclassesOfGraphScanner, scope=injector.singleton)

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
            FunctionParserConnector
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
        for parser_type, ty in parser_types.items():
            binder.bind(ty, ty, scope=injector.singleton)
        binder.multibind(typing.List[StatementParser], lambda: [
            InjectionContext.get_interface(ty) for parser_type, ty
            in parser_types.items()
        ], scope=injector.singleton)
        binder.bind(AggregateStatementParser, AggregateStatementParser, scope=injector.singleton)
