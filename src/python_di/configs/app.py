import functools
import typing

from python_di.configs.boot import _boot


def boot_application(root_dir_cls: typing.Optional[typing.Type] = None,
                     root_dir_name: typing.Optional[str] = None):
    @functools.wraps(boot_application)
    def boot_app_inner(cls):
        _boot(cls, root_dir_cls, root_dir_name)

        return cls

    return boot_app_inner



