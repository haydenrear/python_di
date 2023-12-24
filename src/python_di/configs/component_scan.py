import importlib
import os
import typing

from python_util.logger.logger import LoggerFacade


def component_scan(base_packages: list[str] = None,
                   base_classes: typing.List[typing.Type] = None):
    """
    :param base_packages:
    :param base_classes: To interpret and add to context - as component scan can be based on components interpreted.
    :return:
    """

    def component_scan_decorator(cls):
        cls.component_scan = True
        cls.sources = [i for i in create_sources(base_packages, base_classes)]
        return cls

    return component_scan_decorator


def create_sources(base_packages: list[str] = None,
                   base_classes: typing.List[typing.Type] = None) -> set[str]:
    sources = set([])
    visited = set([])
    visited_cls = set([])
    if base_packages is None:
        base_packages = []
    for b in filter(lambda v: v not in visited_cls, base_classes):
        base_packages.append(b.__module__)
        visited_cls.add(b)

    for b in filter(lambda v: v not in visited, base_packages):
        try:
            visited.add(b)
            imported_mod = importlib.import_module(b)
            if hasattr(imported_mod, '__file__'):
                directory_found = os.path.dirname(imported_mod.__file__)
                add_source_recursive(directory_found, sources, visited)
            else:
                LoggerFacade.error(f"{imported_mod} did not have file attribute")
        except Exception:
            LoggerFacade.error(f"Failed to import {b}.")

    return sources


def is_valid_dir(directory_found):
    return '__pycache__' not in directory_found


def add_source_recursive(directory_found, to_add, visited):
    if os.path.isdir(directory_found):
        if is_valid_dir(directory_found):
            to_add.add(directory_found)
            visited.add(directory_found)
            for sub_dir in os.listdir(directory_found):
                LoggerFacade.debug_deferred(lambda: f"Adding {sub_dir} to component scan")
                add_source_recursive(os.path.join(directory_found, sub_dir), to_add, visited)
