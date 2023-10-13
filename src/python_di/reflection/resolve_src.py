import enum
import importlib.util
import os

import ast
import importlib.util
import os

import ast


def resolve_import_name(class_name, source_code):
    import_name = None
    tree = ast.parse(source_code)
    imports = []

    for node in ast.walk(tree):
        # Collect import information
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append({"module": n.name, "alias": n.asname})
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                imports.append({"module": f"{node.module}.{n.name}", "alias": n.asname})

    # Resolve the full import name based on the class name
    for imp in imports:
        if imp["alias"] == class_name:
            import_name = imp["module"]
            break
        elif imp["module"].split(".")[-1] == class_name:
            import_name = imp["module"]
            break

    return import_name


def get_module_path(module_name):
    # Find the module based on the name and get its spec
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return None

    # Return the path of the module's source file
    return spec.origin


def get_next_source_file(class_name):
    # Assume the module name is the same as the class name
    # You may need to adjust this based on your project structure
    module_path = get_module_path(class_name)
    if module_path is None:
        print(f"Module {class_name} not found.")
        return None

    # Verify the file exists
    if not os.path.exists(module_path):
        print(f"File {module_path} does not exist.")
        return None

    # Read the content of the file
    with open(module_path, "r") as file:
        source = file.read()
        return source



def get_file_dir_from_relative_import(relative_import, current_file):
    """
    Load and parse a relative import.

    Parameters:
        relative_import (str): The relative import path.
        current_file (str): The file path of the current Python file.

    Returns:
        classes (list): A list of classes in the imported file.
        functions (list): A list of functions in the imported file.
    """
    # Convert relative import to absolute import
    base_dir = os.path.dirname(current_file)
    abs_import = os.path.join(base_dir, relative_import)
    abs_import = os.path.abspath(abs_import)

    # Check if the absolute import path is a valid file
    if not os.path.isfile(abs_import):
        raise ValueError(f"Invalid relative import path: {relative_import}")

    return abs_import



class ImportType(enum.Enum):
    MultipleImport = enum.auto()
    AliasImport = enum.auto
    AbsoluteImport = enum.auto()
    ExplicitRelativeImport = enum.auto()
    WildcardImport = enum.auto()
    SelectiveImport = enum.auto()




class ImportResolver:

    @classmethod
    def resolve_module_import(cls, import_type, node, cur_file):
        if import_type == ImportType.SelectiveImport:
            return cls.resolve_selective_import(node, cur_file)
        elif import_type == ImportType.WildcardImport:
            return cls.resolve_wildcard_import(node, cur_file)
        elif import_type == ImportType.AliasImport:
            return cls.resolve_alias_import(node, cur_file)
        elif import_type == ImportType.AbsoluteImport:
            return cls.resolve_absolute_import(node, cur_file)
        elif import_type == ImportType.ExplicitRelativeImport:
            return cls.resolve_relative_import(node, cur_file)
        elif import_type == ImportType.MultipleImport:
            return cls.resolve_multiple_import(node, cur_file)


    @classmethod
    def resolve_absolute_import(cls, node, cur_file):
        module_name = node.names[0].name
        cur_file = os.path.dirname(cur_file)
        return cls._get_module_path(module_name, cur_file)

    @classmethod
    def resolve_relative_import(cls, node, cur_file):
        module_name = '.' * node.level + node.module
        cur_file = os.path.dirname(cur_file)
        return get_file_dir_from_relative_import(module_name, cur_file)

    @classmethod
    def resolve_multiple_import(cls, node, cur_file):
        cur_file = os.path.dirname(cur_file)
        return [cls._get_module_path(name, cur_file) for name in node.name]

    @classmethod
    def resolve_alias_import(cls, node, cur_file):
        module_name = node.name[0]
        return cls._get_module_path(module_name, os.path.dirname(cur_file))

    @classmethod
    def resolve_wildcard_import(cls, node, cur_file):
        module_name = node.module
        return cls._get_module_path(module_name, os.path.dirname(cur_file))

    @classmethod
    def resolve_selective_import(cls, node, cur_file):
        module_name = node.module
        return cls._get_module_path(module_name, os.path.dirname(cur_file))

    @classmethod
    def _get_absolute_import(cls, node, cur_file):
        return cls._get_module_path(node.module, os.path.dirname(cur_file))

    @classmethod
    def _get_import(cls, nodes, name):
        for node in nodes:
            if isinstance(node, ast.Import):
                if any([n.name == name or n.asname == name for n in node.names]):
                    return node
            elif isinstance(node, ast.ImportFrom):
                if any([n.name == name or n.asname == name for n in node.names]):
                    return node

    @classmethod
    def _get_module_path(cls, module_name, current_dir):
        module_import = importlib.import_module(module_name)
        if module_import is not None and module_import.__file__ is not None:
            import_file = module_import.__file__
            return import_file

        path_components = module_name.split('.')

        if path_components[0] == '':
            # Relative import
            relative_level = len(path_components) - 1
            module_dir = os.path.join(current_dir, *(['..'] * relative_level))
            module_name = path_components[-1]
        else:
            # Absolute import
            module_dir = current_dir

        module_path = os.path.join(module_dir, *path_components[1:], module_name + '.py')
        if os.path.exists(module_path):
            return module_path

        # Check for package (directory with __init__.py)
        package_path = os.path.join(module_dir, *path_components[1:], '../../src/drools_py/reflection/__init__.py')
        if os.path.exists(package_path):
            return package_path
        else:
            dir_name = module_dir
            while dir_name and dir_name != '/' and dir_name != '':
                dir_name = os.path.dirname(dir_name)
                potential_package_path = cls._get_module_path_recursive(module_name, dir_name)
                if potential_package_path is not None:
                    return potential_package_path
                for inner_dir in os.listdir(dir_name):
                    potential_package_path = cls._get_module_path_recursive(module_name, os.path.join(dir_name,
                                                                                                      inner_dir))
                    if potential_package_path is not None:
                        return potential_package_path

        return None

    @classmethod
    def _get_module_path_recursive(cls, module_name, current_dir):
        path_components = module_name.split('.')
        if path_components[0] == '':
            # Relative import
            relative_level = len(path_components) - 1
            module_dir = os.path.join(current_dir, *(['..'] * relative_level))
            module_name = path_components[-1]
        else:
            # Absolute import
            module_dir = current_dir

        file_name = path_components[-1:][0] + '.py'
        directory_name = path_components[:-1]
        module_path = os.path.join(module_dir, *directory_name, file_name)
        if os.path.exists(module_path):
            return module_path

