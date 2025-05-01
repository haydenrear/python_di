
DEFAULT_PROFILE: str = 'main_profile'
DEFAULT_PRIORITY = 1000000

def get_default_profile():
    from python_di.env.profile import Profile
    return Profile(profile_name=DEFAULT_PROFILE, priority=DEFAULT_PRIORITY)