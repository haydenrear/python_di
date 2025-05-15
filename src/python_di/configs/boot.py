import importlib
import inspect
import os
import typing

from python_util.logger.logger import LoggerFacade

from python_util.io_utils.file_dirs import find_file

def _parse_dir(profile_name_override = None, root_dir = None):
    stack_to_search = inspect.stack()

    found_dir = None
    if root_dir is not None:
        booter_source_file = root_dir
        found_dir = find_file(booter_source_file, f'.{profile_name_override}_env' if profile_name_override is not None else '.env')
        if found_dir is not None:
            return found_dir
    if len(stack_to_search) > 1:
        if found_dir is None:
            for s in stack_to_search[1:]:
                LoggerFacade.info("Searching for .env file from booter.")
                booter = s
                booter_source_file = booter.filename
                found_dir = find_file(booter_source_file, f'.{profile_name_override}_env' if profile_name_override is not None else '.env')
                if found_dir is not None:
                    return found_dir
        LoggerFacade.info(f"Found .env - {found_dir}")
    else:
        LoggerFacade.info("Could not search for .env - stack was not big enough.")

def _build_ctx(package_root_directory, scan_root, profile_name_override = None):
    parsed_env = _parse_dir(profile_name_override, package_root_directory)
    from python_di.inject.context_builder.injection_context import InjectionContext
    assert package_root_directory is not None and scan_root is not None, "root directory was None."
    LoggerFacade.info(f"Found {package_root_directory} and {scan_root} when building context.")
    inject_ctx = InjectionContext()
    env = inject_ctx.initialize_env(profile_name_override, parsed_env)
    assert env is not None
    inject_ctx.build_context({scan_root}, package_root_directory)


def _boot(cls,
          package_root_module: typing.Optional[typing.Type] = None,
          source_root_directory: typing.Optional[str] = None,
          scan_root_module: typing.Optional[typing.Type] = None,
          scan_root_directory: typing.Optional[str] = None,
          profile_name_override = None):
    if source_root_directory is not None:
        package_root_directory = source_root_directory
    else:
        package_root_directory = importlib.import_module(cls.__module__) \
            if package_root_module is None \
            else importlib.import_module(package_root_module.__module__)
        package_root_directory = package_root_directory.__file__
    if scan_root_module is not None:
        scan_root = importlib.import_module(scan_root_module.__module__).__file__
        _build_ctx(package_root_directory, scan_root, profile_name_override)
    elif scan_root_directory is not None:
        _build_ctx(package_root_directory, scan_root_directory, profile_name_override)
    else:
        root_dir_introspected = os.path.dirname(os.path.dirname(package_root_directory))
        LoggerFacade.warn(f"No root directory provided for boot application. "
                          f"Using {root_dir_introspected}")
        _build_ctx(package_root_directory, root_dir_introspected, profile_name_override)
