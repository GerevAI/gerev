import ast
import os
import re
from dataclasses import dataclass
from typing import Dict
import importlib

from data_source.api.utils import snake_case_to_pascal_case


@dataclass
class ClassInfo:
    name: str
    file_path: str


class DynamicLoader:
    """
    This class is used to dynamically load classes from files.
    Specifically, it is used to load data sources from the data_source/sources directory.
    """
    SOURCES_PATH = os.path.join('data_source', 'sources')

    @staticmethod
    def extract_classes(file_path: str):
        with open(file_path, 'r') as f:
            file_ast = ast.parse(f.read())
            classes = {}
            for node in file_ast.body:
                if isinstance(node, ast.ClassDef):
                    classes[node.name] = {'node': node, 'file': file_path}
        return classes

    @staticmethod
    def get_data_source_class(data_source_name: str):
        class_name = f"{snake_case_to_pascal_case(data_source_name)}DataSource"
        class_file_path = DynamicLoader.find_class_file(DynamicLoader.SOURCES_PATH, class_name)
        return DynamicLoader.get_class(class_file_path, class_name)

    @staticmethod
    def get_class(file_path: str, class_name: str):
        
        module_name = file_path.replace("/", ".").replace(".py", "")
        loader = importlib.machinery.SourceFileLoader(class_name, file_path)
        module = loader.load_module()
        try:
            return getattr(module, class_name)
        except AttributeError:
            raise AttributeError(f"Class {class_name} not found in module {module},"
                                 f"make sure you named the class correctly (it should be <Platform>DataSource)")

    @staticmethod
    def find_class_file(directory, class_name):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    classes = DynamicLoader.extract_classes(file_path)
                    if class_name in classes:
                        return file_path
        return None

    @staticmethod
    def find_data_sources() -> Dict[str, ClassInfo]:
        all_classes = {}
        # First, extract all classes and their file paths
        for root, dirs, files in os.walk(DynamicLoader.SOURCES_PATH):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    all_classes.update(DynamicLoader.extract_classes(file_path))

        def is_base_data_source(class_name: str):
            if class_name not in all_classes:
                return False

            class_info = all_classes[class_name]
            node = class_info['node']

            for base in node.bases:
                if isinstance(base, ast.Name):
                    if base.id == 'BaseDataSource':
                        return True
                    elif is_base_data_source(base.id):
                        return True

            return False

        data_sources = {}
        # Then, check if each class inherits from BaseDataSource
        for class_name, class_info in all_classes.items():
            if is_base_data_source(class_name):
                snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                                    re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)).lower()
                clas_name = snake_case.replace('_data_source', '')
                data_sources[clas_name] = ClassInfo(name=class_name,
                                                    file_path=class_info['file'])

        return data_sources


if __name__ == '__main__':
    print(DynamicLoader.find_data_sources())
