import importlib
import logging
import os
from typing import Optional

import injector
from dotenv import load_dotenv

from python_util.logger.logger import LoggerFacade


def retrieve_env_profile():
    from python_di.env.profile import Profile
    from python_di.env.env_properties import YAML_ENV_PROFILE, YAML_ENV_PRIORITY
    return Profile.new_profile(YAML_ENV_PROFILE, YAML_ENV_PRIORITY)


def import_load(provider: str):
    provider = provider.split(".")
    module = importlib.import_module(str.join('.', provider[0:len(provider) - 1]))

    try:
        to_return = module.__dict__[provider[len(provider) - 1]]
        LoggerFacade.info(f'Imported module {to_return}.')
        file_env = to_return()
        return file_env
    except Exception as e:
        LoggerFacade.error(f"Failed to initialize {provider[len(provider) - 1]}: {e}")


def get_env_module(name: Optional[str] = None):
    """
    The environment module is loaded from the .env file, and then the other modules are loaded from the factories
    property of the resources loaded from the environment module.
    :return:
    """
    if name is not None:
        if not load_dotenv(name):
            logging.error("Error loading .env file.")
    if "ENV_FILE_PATH" in os.environ.keys():
        load_dotenv(os.environ["ENV_FILE_PATH"])
    else:
        load_dotenv()
    provider = os.environ["ENV_PROVIDER"]
    return import_load(provider)


class EnvironmentProvider(injector.Module):

    def __init__(self, env):
        self.env = env

    def configure(self, binder: injector.Binder) -> None:
        from python_di.env.base_env_properties import Environment
        binder.bind(Environment, to=self.env, scope=injector.SingletonScope)
