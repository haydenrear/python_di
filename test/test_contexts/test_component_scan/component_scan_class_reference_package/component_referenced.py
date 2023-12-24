import injector

from python_di.configs.component import component


@component()
class ComponentReferenced:
    @injector.inject
    def __init__(self):
        pass
