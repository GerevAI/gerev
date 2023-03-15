import importlib


def get_class_by_data_source_name(data_source_name: str):
    class_name = f"{data_source_name.capitalize()}DataSource"

    module = importlib.import_module(f"data_sources.{data_source_name}")

    try:
        return getattr(module, class_name)
    except AttributeError:
        raise AttributeError(f"Class {class_name} not found in module {module},"
                             f"make sure you named the class correctly (it should be <Platform>DataSource)")
