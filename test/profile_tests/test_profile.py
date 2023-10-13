import unittest

from python_di.env.profile_config_props import ProfileProperties
from python_di.inject.injector_provider import InjectionContext


class ProfileTest(unittest.TestCase):
    def test_profile_fallback(self):
        profile: ProfileProperties = InjectionContext.get_interface(ProfileProperties)
        assert profile.active_profiles == ['test']


if __name__ == '__main__':
    unittest.main()
