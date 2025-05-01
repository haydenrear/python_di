import importlib
import os
import typing

from python_util.logger.logger import LoggerFacade


def _build_ctx(package_root_directory, scan_root, profile_name_override = None):
    from python_di.inject.context_builder.injection_context import InjectionContext
    assert package_root_directory is not None and scan_root is not None, "root directory was None."
    LoggerFacade.info(f"Found {package_root_directory} and {scan_root} when building context.")
    inject_ctx = InjectionContext()
    env = inject_ctx.initialize_env(profile_name_override)
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
