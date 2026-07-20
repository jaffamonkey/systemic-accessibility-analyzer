import pkgutil
import importlib
from adapters import nu_html_checker

def load_adapters():

    package = __name__

    for _, module_name, _ in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{package}.{module_name}")