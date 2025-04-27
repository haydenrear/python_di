import functools
import inspect
import os
import typing

from python_di.inject.context_builder.injection_context import InjectionContext
from python_util.logger.logger import LoggerFacade


def boot_application(root_dir_cls: typing.Optional[typing.Type] = None,
                     root_dir_name: typing.Optional[str] = None):

    if root_dir_name is None:
        s = inspect.stack()[1].filename
        root_dir_name=os.path.dirname(os.path.dirname(s))
        LoggerFacade.info(f"Initialized root with {root_dir_name}")

    @functools.wraps(boot_application)
    def boot_app_inner(cls):
        inject_ctx = InjectionContext()
        env = inject_ctx.initialize_env()

        inject_ctx.build_context(parent_sources={root_dir_name}, source_directory=os.path.dirname(root_dir_name))

        if root_dir_cls is not None:
            found = inject_ctx.ctx.get_interface(root_dir_cls)
            if found:
                LoggerFacade.info(f"Initialized {found}.")

        return cls

    return boot_app_inner


