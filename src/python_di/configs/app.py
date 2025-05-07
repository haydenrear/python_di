import functools
import inspect
import os
import typing

import python_util.io_utils.file_dirs
from python_di.inject.context_builder.injection_context import InjectionContext
from python_util.logger.logger import LoggerFacade


def boot_application(root_dir_cls: typing.Optional[typing.Type] = None,
                     root_dir_name: typing.Optional[str] = None,
                     profile_name_override = None):

    if root_dir_name is None:
        s = inspect.stack()[1].filename
        root_dir_name=os.path.dirname(os.path.dirname(s))
        LoggerFacade.info(f"Initialized root with {root_dir_name}")

    @functools.wraps(boot_application)
    def boot_app_inner(cls):
        inject_ctx = InjectionContext()

        stack_to_search = inspect.stack()
        if len(stack_to_search) > 1:
            LoggerFacade.info("Searching for .env file from booter.")
            booter = inspect.stack()[1]
            booter_source_file = booter.filename
            found_dir = python_util.io_utils.file_dirs.find_file(booter_source_file, '.env')
            LoggerFacade.info(f"Found .env - {found_dir}")
        else:
            LoggerFacade.info("Could not search for .env - stack was not big enough.")
            found_dir = None

        env = inject_ctx.initialize_env(profile_name_override, found_dir)

        inject_ctx.build_context(parent_sources={root_dir_name}, source_directory=os.path.dirname(root_dir_name))

        if root_dir_cls is not None:
            found = inject_ctx.ctx.get_interface(root_dir_cls)
            if found:
                LoggerFacade.info(f"Initialized {found}.")

        return cls

    return boot_app_inner


