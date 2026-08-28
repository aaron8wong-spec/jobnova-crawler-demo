# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
import importlib
import pkgutil
from scrapy import Spider
import inspect
import os

main_spiders = []

main_classes = []
# load classes subclass of Spider
classes = []

spiders_dir = os.path.dirname(__file__)

for root, _, files in os.walk(spiders_dir):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            module_path = os.path.splitext(os.path.relpath(os.path.join(root, file), start=os.path.dirname(os.path.dirname(spiders_dir))))[0].replace(os.sep, '.')
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                continue
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"Failed to load {module_path}: {e}")
                continue
            for name, value in inspect.getmembers(module):
                globals()[name] = value
                if inspect.isclass(value) and issubclass(value, Spider) and value is not Spider \
                        and not getattr(value, 'ignore', False):
                    if value.__name__ in main_spiders:
                        main_classes.append(value)
                    classes.append(value)

__all__ = __ALL__ = classes

__main_cls__ = main_classes

__nomal_cls__ = list(set(classes) - set(main_classes))
