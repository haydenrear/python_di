def set_add_context_factory(items, cls):
    if hasattr(cls, 'context_factory'):
        cls.context_factory.extend(items)
    else:
        cls.context_factory = items

