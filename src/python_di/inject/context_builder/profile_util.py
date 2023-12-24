import typing

from python_util.logger.logger import LoggerFacade

DEFAULT_PRIORITY = -100
ProfileT = typing.TypeVar("ProfileT")


def create_add_default_profile(profile_props, priority, profile):
    LoggerFacade.debug(f"Requested profile with name {profile}, "
                       f"but did not exist yet in prioritized injectors retrieve profile.")
    from python_di.env.profile import Profile
    assert isinstance(profile, str)
    if priority is None:
        priority = DEFAULT_PRIORITY
    new_profile = Profile.new_profile(profile, priority)
    profile_props[profile] = new_profile
    return new_profile


def add_profile(profile_props, priority, profile):
    from python_di.env.profile import Profile
    assert isinstance(profile, Profile)
    profile_props[profile.profile_name] = profile


def create_add_profile_curry(
        priority, profile,
        cb: typing.Callable[[ProfileT, int, ProfileT], object] = create_add_default_profile):
    LoggerFacade.debug(f"Requested profile with name {profile}, "
                       f"but did not exist yet in prioritized injectors retrieve profile.")
    return lambda profile_props: cb(profile_props, priority, profile)
