import abc
import ast
import typing

import injector

from python_util.ordered.ordering import Ordered


class IntrospectedDef:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        to_return_str = f'{str(type(self))}:\n'
        for key, val in self.__dict__.items():
            to_return_str += f'{key}: {str(val)}\n'
        return to_return_str

    def __hash__(self):
        return hash(tuple(i for i in self.get_introspected_children() if i != self))

    def get_introspected_children(self) -> list:
        to_return = []
        to_return.append(self)
        for val in self.__dict__.values():
            if isinstance(val, list) and len(val) != 0:
                for v in val:
                    if isinstance(v, IntrospectedDef):
                        to_return.extend(v.get_introspected_children())
            if isinstance(val, IntrospectedDef):
                to_return.extend(val.get_introspected_children())

        return to_return

    def get_introspected_tree(self):
        value: dict = {self.name: {'self_param': self}}
        for val in self.__dict__.values():
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, IntrospectedDef):
                        next_values = v.get_introspected_tree()
                        for key, val in next_values.items():
                            value[self.name][key] = val
            elif isinstance(val, IntrospectedDef):
                next_values = val.get_introspected_tree()
                for key, val in next_values.items():
                    value[self.name][key] = val

        return value

    def get_class_deps(self) -> list[str]:
        class_deps = [self.name]
        for i in self.get_introspected_children():
            if i != self:
                class_deps.extend(i.get_class_deps())

        return class_deps

    def remove_path(self):
        self.name = self.name.split('.')[-1]
        for i in self.get_introspected_children():
            if i != self:
                i.remove_path()


class IntrospectedDict(IntrospectedDef):
    def __init__(self, key: IntrospectedDef,
                 value: IntrospectedDef, name):
        super().__init__(name)
        self.key = key
        self.value = value


class IntrospectedList(IntrospectedDef):
    def __init__(self, list_values: IntrospectedDef, name):
        super().__init__(name)
        self.list_values = list_values


class IntrospectedOptional(IntrospectedDef):
    def __init__(self, opt_type: IntrospectedDef, name):
        super().__init__(name)
        self.opt_type = opt_type


class IntrospectedGeneric(IntrospectedDef):
    def __init__(self, gen_types: list[IntrospectedDef], name):
        super().__init__(name)
        self.gen_types = gen_types


class TypeIntrospector(abc.ABC):

    def __init__(self):
        self.agg = None

    @abc.abstractmethod
    def matches(self, base):
        pass

    @abc.abstractmethod
    def introspect_type_inner(self, base) -> (object, IntrospectedDef | list[IntrospectedDef]):
        pass

    def set_agg(self, agg):
        self.agg = agg


class AggregateTypeIntrospecter(TypeIntrospector):
    @injector.inject
    def __init__(self, introspecters: typing.List[TypeIntrospector]):
        super().__init__()
        self.introspecters = introspecters
        self.set_agg(self)
        for introspecter in self.introspecters:
            introspecter.set_agg(self)

    def matches(self, base):
        return any([i.matches(base) for i in self.introspecters])

    def introspect_type(self, base) -> list[IntrospectedDef]:
        introspected = []
        for i in self.introspecters:
            if i.matches(base):
                inner = i.introspect_type_inner(base)
                introspected.extend(inner[1])
        return introspected

    def introspect_type_inner(self, base) -> (object, list[IntrospectedDef]):
        for i in self.introspecters:
            if i.matches(base):
                return i.introspect_type_inner(base)


class AttributeAstIntrospecter(TypeIntrospector):

    def __init__(self):
        super().__init__()

    def matches(self, base):
        return isinstance(base, ast.Attribute)

    def introspect_type_inner(self, base) -> (object, list[IntrospectedDef]):
        assert isinstance(base, ast.Attribute)
        type_attr = base.attr
        inner, ty = self.agg.introspect_type_inner(base.value)
        return f'{inner}.{type_attr}', ty if isinstance(ty, list) else [ty]


class ListAstIntrospecter(TypeIntrospector):

    def __init__(self):
        super().__init__()

    def matches(self, base):
        return isinstance(base, ast.List)

    def introspect_type_inner(self, base: ast.List) -> (object, list[IntrospectedDef]):
        ty_s = [self.agg.introspect_type_inner(b) for b in base.elts if b]
        s_ = []
        for ty in ty_s:
            if len(ty[1]) != 0:
                s_.append(ty[1][0])
            else:
                s_.append('None')
        return ','.join([ty[0] for ty in ty_s if ty is not None]), s_


class NameIntrospecter(TypeIntrospector):
    def matches(self, base):
        return isinstance(base, ast.Name)

    def introspect_type_inner(self, base: ast.Name) -> (object, list[IntrospectedDef]):
        return base.id, [IntrospectedDef(name=base.id)]


class ConstantIntrospecter(TypeIntrospector):
    def matches(self, base):
        return isinstance(base, ast.Constant)

    def introspect_type_inner(self, base: ast.Constant) -> (object, list[IntrospectedDef]):
        return str(base.value), [IntrospectedDef(name=str(base.value))]


class TupleIntrospecter(TypeIntrospector):

    def matches(self, base):
        return isinstance(base, ast.Tuple)

    def introspect_type_inner(self, base: ast.Tuple) -> (object, list[IntrospectedDef]):
        ty_s = [self.agg.introspect_type_inner(b) for b in base.dims if b]
        s_ = []
        for ty in ty_s:
            if len(ty[1]) != 0:
                s_.append(ty[1][0])
            else:
                s_.append('None')
        return ','.join([ty[0] for ty in ty_s if ty is not None]), s_


class ClassDefIntrospectParser(Ordered, abc.ABC):

    @abc.abstractmethod
    def parse_type(self, ty, name, inner) -> list[IntrospectedDef]:
        pass

    @abc.abstractmethod
    def matches(self, ty, name, inner) -> bool:
        pass


class OptionalClassDefParser(ClassDefIntrospectParser):

    def matches(self, ty, name, inner) -> bool:
        is_opt = inner.lower() == 'optional' or 'optional' in inner.lower()
        return is_opt

    def order(self) -> int:
        return 2

    def parse_type(self, ty, name, inner) -> list[IntrospectedOptional]:
        assert len(ty) == 1, \
            "Optional requires 1 type"
        return [IntrospectedOptional(name=name, opt_type=ty[0])]


class ListClassDefParser(ClassDefIntrospectParser):

    def matches(self, ty, name, inner) -> bool:
        is_list = inner.lower() == 'list' or inner.lower() == 'typing.list'
        if is_list:
            return True
        # else:
        #     try:
        #         value = eval(inner)()

    def order(self) -> int:
        return 0

    def parse_type(self, ty, name, inner) -> list[IntrospectedDef]:
        return [IntrospectedList(name=name, list_values=ty[0])]


class DictClassDefParser(ClassDefIntrospectParser):

    def matches(self, ty, name, inner) -> bool:
        is_dict = (inner.lower() == 'dict' or inner.lower() == 'typing.dict'
                   or inner.lower() == typing.OrderedDict.__name__.lower()
                   or inner.lower() == typing.TypedDict.__name__.lower()
                   or inner.lower() == typing.DefaultDict.__name__.lower())
        return is_dict

    def order(self) -> int:
        return 1

    def parse_type(self, ty, name, inner) -> list[IntrospectedDef]:
        return [IntrospectedDict(name=name, key=ty[0], value=ty[1])]


class GenericClassDefParser(ClassDefIntrospectParser):

    def matches(self, ty, name, inner) -> bool:
        return len(ty) != 0

    def order(self) -> int:
        return 3

    def parse_type(self, ty, name, inner) -> list[IntrospectedDef]:
        if len(ty) == 1 and len(ty[0].name) == 1:
            return [IntrospectedGeneric(name=name, gen_types=[ty[0]])]
        elif len(ty) == 1:
            return [IntrospectedGeneric(name=name, gen_types=[ty[0]])]
        elif len(ty) == 2:
            return [IntrospectedGeneric(name=name, gen_types=[ty[0], ty[1]])]
        elif 'Union' in inner:
            return [IntrospectedGeneric(name=name, gen_types=[t for t in ty])]
        else:
            assert len(ty) == 0, \
                f"Unsupported generic type for {name}."
            return [IntrospectedGeneric(name=name, gen_types=[])]


class SubscriptIntrospecter(TypeIntrospector):

    @injector.inject
    def __init__(self, class_def_parsers: typing.List[ClassDefIntrospectParser]):
        super().__init__()
        self.class_def_parsers = list(sorted(class_def_parsers, key=lambda x: x.order()))

    def matches(self, base):
        return isinstance(base, ast.Subscript)

    def introspect_type_inner(self, base) -> (object, list[IntrospectedDef]):
        if base.value:
            inner, ty = self.agg.introspect_type_inner(base.value)
        else:
            inner = base
        outer, ty = self.agg.introspect_type_inner(base.slice)

        name = f'{inner}[{outer}]'
        for class_def_parser in self.class_def_parsers:
            if class_def_parser.matches(ty, name, inner):
                return name, class_def_parser.parse_type(ty, name, inner)

        return name, [IntrospectedDef(name)]