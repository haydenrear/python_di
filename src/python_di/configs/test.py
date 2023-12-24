import importlib
import os
import typing

import python_util.io_utils.file_dirs
from python_di.configs.boot import _boot
from python_di.configs.constants import DiUtilConstants
from python_di.configs.di_util import get_wrapped_fn


def test_booter(scan_root_module: typing.Optional[typing.Type] = None,
                scan_root_directory: typing.Optional[str] = None):
    def boot_test_inner(cls):
        package_root_directory = python_util.io_utils.file_dirs.get_dir(importlib.import_module(cls.__module__).__file__,
                                                                        'src')
        if scan_root_module is not None:
            scan_root_directory_created = os.path.dirname(importlib.import_module(scan_root_module.__module__).__file__)
            _boot(cls, None, package_root_directory, None, scan_root_directory_created)
        else:
            _boot(cls, None, package_root_directory, scan_root_module, scan_root_directory)

        return cls

    return boot_test_inner


def boot_test(ctx: typing.Type):
    """
    Imports a type decorated with test_booter and calls all test_inject decorators to inject.
    :param ctx:
    :return:
    """
    def boot_test_inner(cls):
        class BootTestProxy(cls):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                value = cls.__dict__.items()
                to_call_test_inject = []
                for k, v in value:
                    if hasattr(v, DiUtilConstants.wrapped_fn.name):
                        callable_fn, wrapped = get_wrapped_fn(v)
                        if hasattr(callable_fn, "is_test_inject"):
                            to_call_test_inject.append(callable_fn)
                for to_call in to_call_test_inject:
                    to_call(self)

        return BootTestProxy

    return boot_test_inner
