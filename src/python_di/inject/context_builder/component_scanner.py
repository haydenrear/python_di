import importlib
import os.path
import sys
import typing

import injector

import python_util.io_utils.file_dirs
from python_di.configs.constants import ContextDecorators
from python_di.inject.context_factory.base_context_factory import ContextFactory
from python_di.inject.context_factory.context_factory_executor.context_factories_executor import InjectionContextArgs
from python_di.inject.context_factory.context_factory_extractor.context_factory_extract import ContextFactoryExtract
from python_di.reflect_scanner.graph_scanner import ModulesOfGraphScanner, DecoratorOfGraphScanner, \
    DecoratorOfGraphScannerArgs, ModulesOfNodesArgs, ModulesOfGraphScannerResult
from python_di.reflect_scanner.module_graph_models import GraphType, ProgramNode
from python_util.logger.logger import LoggerFacade


class ComponentScanner:

    @injector.inject
    def __init__(self, context_factory_extract: typing.List[ContextFactoryExtract],
                 module_scanner: ModulesOfGraphScanner,
                 decorator_scanner: DecoratorOfGraphScanner):
        self.decorator_scanner = decorator_scanner
        self.module_scanner = module_scanner
        self.context_factory_extract = context_factory_extract

    def produce_sources(self, inject_context_args: InjectionContextArgs) -> set[str]:
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        assert isinstance(inject_context_args, InjectionContextInjectorContextArgs)
        out_sources = set([])

        codegen_value = python_util.io_utils.file_dirs.get_dir(inject_context_args.starting,
                                                               'codegen')
        if codegen_value is not None:
            out_sources.add(codegen_value)

        scanned = self._retrieve_decorated(inject_context_args, 'component_scan')

        for s in scanned:
            self._add_component_scan(out_sources, s, inject_context_args)

        return out_sources

    def _add_component_scan(self, out_sources, s, inject_context_args):
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        if hasattr(s, 'component_scan') and hasattr(s, 'sources'):
            for source_to_add in s.sources:
                if source_to_add not in out_sources:
                    out_sources.add(source_to_add)
                    for n_s in self._retrieve_decorated(InjectionContextInjectorContextArgs(
                            inject_context_args.injection_context_injector,
                            {source_to_add},
                            inject_context_args.starting
                    ), 'component_scan'):
                        self._add_component_scan(out_sources, n_s, inject_context_args)

        else:
            LoggerFacade.error(f"Retrieved component scan {s} that did not contain sources.")

    def scan_context_factories(self, inject_context_args: InjectionContextArgs) -> list[ContextFactory]:
        out_factories = []
        for decorator_id in ContextDecorators.context_ids():
            out_factories.extend(self._retrieve_factories_from_decorated(inject_context_args, decorator_id))

        return out_factories

    def _retrieve_factories_from_decorated(self, args, decorator_id):
        configs = self._retrieve_decorated(args, decorator_id)
        out_factories = []
        for c in configs:
            for f in self.context_factory_extract:
                if f.matches(c):
                    next_factories = f.extract_context_factory(c)
                    out_factories.extend(next_factories)
        return out_factories

    def _retrieve_src(self, args: InjectionContextArgs) -> set[str]:
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        assert isinstance(args, InjectionContextInjectorContextArgs)
        return args.sources

    def _retrieve_decorated(self, args: InjectionContextArgs, decorator_id: str) -> list[typing.Type]:
        from python_di.inject.context_builder.injection_context import InjectionContextInjectorContextArgs
        assert isinstance(args, InjectionContextInjectorContextArgs)
        env = args.injection_context_injector
        source = args.sources
        configs = []

        program_graph = self._parse_program(env, source)

        decorated = self.decorator_scanner.do_scan(DecoratorOfGraphScannerArgs(decorator_id, program_graph,
                                                                               GraphType.Program))
        with_module = self.module_scanner.do_scan(ModulesOfNodesArgs(program_graph, GraphType.Program,
                                                                     decorated.nodes))

        nodes_grouped = self.group_by_module(with_module)
        for module_scanned, node_scanned in nodes_grouped.items():
            module_scanned: ProgramNode = module_scanned
            id_value = module_scanned.id_value
            if id_value is not None:
                node_scanned: list[ProgramNode] = node_scanned
                next_config = self._import_module(args, decorator_id, id_value, module_scanned, node_scanned)
                LoggerFacade.debug(f"Imported {next_config}")
                configs.extend(next_config)
            else:
                LoggerFacade.error(f"Could not parse module: {id_value} from {module_scanned} and {node_scanned}.")

        return configs

    @staticmethod
    def _parse_program(env, source):
        from python_di.reflect_scanner.program_parser import ProgramParser, ListBasedSourceFileProvider
        next_file_parser: ProgramParser = env.get_interface(ProgramParser, scope=injector.noscope)
        source_file_provider = ListBasedSourceFileProvider([i for i in source])
        next_file_parser.set_source_file_provider(source_file_provider)
        next_file_parser.do_parse()
        return next_file_parser.program_graph

    @classmethod
    def group_by_module(cls, module_nodes: ModulesOfGraphScannerResult):
        out_nodes = {}
        for (module_scanned, node_scanned) in module_nodes.nodes:
            if module_scanned in out_nodes:
                out_nodes[module_scanned].append(node_scanned)
            else:
                out_nodes[module_scanned] = [node_scanned]

        return out_nodes

    @classmethod
    def _import_module(cls, args, decorator_id, id_value, module_scanned, node_scanned: list[ProgramNode]):
        try:
            module_imported, next_id_value = cls._try_introspect_import(args, id_value, module_scanned)
        except Exception as exc:
            LoggerFacade.error(f"{id_value} failed from {args.sources} for {decorator_id}")
            raise exc

        return [module_imported.__dict__[n.id_value] for n in node_scanned
                if n.id_value in module_imported.__dict__.keys()]

    @classmethod
    def _try_introspect_import(cls, args, id_value, module_scanned):
        assert args.starting is not None, \
            f"Could not import {id_value} - module does not exist with that name."
        last_exc = None
        for n in cls._parse_module_id(args, module_scanned):
            if n is not None:
                try:
                    module_imported = importlib.import_module(n)
                    return module_imported, n
                except Exception as e:
                    last_exc = e
            else:
                LoggerFacade.error(f"{n} was none for {id_value}.")

        if last_exc is not None:
            raise last_exc

        raise NotImplementedError("Failure.")

    @classmethod
    def _parse_module_id(cls, args, module_scanned):
        yield from [cls._parse_rel(os.path.relpath(module_scanned.source_file, a))
                    for a in sorted(args.sources, key=lambda s: len(s))
                    if module_scanned.source_file.startswith(a)]

        if module_scanned.source_file.startswith(args.starting):
            relativized = os.path.relpath(module_scanned.source_file, args.starting)
            yield cls._parse_rel(relativized)

        yield from [cls._parse_rel(os.path.relpath(module_scanned.source_file, path))
                    for path in sys.path
                    if module_scanned.source_file.startswith(path)]

        raise NotImplementedError("Could not find!")

    @classmethod
    def _parse_rel(cls, relativized):
        next_id_value = relativized.replace("/", ".")
        if next_id_value.startswith("."):
            next_id_value = next_id_value[1:]
        if next_id_value.endswith(".py"):
            next_id_value = next_id_value[:-3]
        return next_id_value
