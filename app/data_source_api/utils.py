import importlib


def _snake_case_to_pascal_case(snake_case_string: str):
    """Converts a snake case string to a PascalCase string"""
    components = snake_case_string.split('_')
    return "".join(x.title() for x in components)


def get_class_by_data_source_name(data_source_name: str):
    class_name = f"{_snake_case_to_pascal_case(data_source_name)}DataSource"

    module = importlib.import_module(f"data_sources.{data_source_name}")

    try:
        return getattr(module, class_name)
    except AttributeError:
        raise AttributeError(f"Class {class_name} not found in module {module},"
                             f"make sure you named the class correctly (it should be <Platform>DataSource)")
