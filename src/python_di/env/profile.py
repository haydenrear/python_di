from python_di.env.base_module_config_props import BaseModuleProps


class Profile(BaseModuleProps):
    profile_name: str
    priority: int = -100

    @classmethod
    def new_profile(cls, profile_name: str, priority: int = -100):
        return Profile(**{
            "profile_name": profile_name,
            "priority": priority
        })

    def __hash__(self):
        return hash((self.profile_name, self.priority))

    def __eq__(self, other):
        return isinstance(other,
                          Profile) and self.profile_name == other.profile_name and self.priority == other.priority

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if not isinstance(other, Profile):
            return True
        else:
            return self.priority > other.priority and self.profile_name > other.profile_name

    def __lt__(self, other):
        if not isinstance(other, Profile):
            return True
        else:
            return self.priority < other.priority and self.profile_name < other.profile_name

    def __le__(self, other):
        if not isinstance(other, Profile):
            return True
        else:
            return self.priority <= other.priority and self.profile_name <= other.profile_name

    def __ge__(self, other):
        if not isinstance(other, Profile):
            return True
        else:
            return self.priority >= other.priority and self.profile_name >= other.profile_name


