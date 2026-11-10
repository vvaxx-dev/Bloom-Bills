"""Entry point supporting both `python3 main.py` and `python3 -m <pkg>.main`."""

import importlib.util
import sys
from pathlib import Path


def bootstrap_package():
    """Register the repository directory as an importable package when run as a top-level script."""
    root = Path(__file__).resolve().parent
    parent = str(root.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    pkg_name = root.name.replace("-", "_")
    if pkg_name and pkg_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(pkg_name, root / "__init__.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = module
        module.__path__ = [str(root)]
        module.__package__ = pkg_name
        module.__spec__ = spec
        module.__file__ = str(root / "__init__.py")
    return pkg_name


if __package__ in (None, ""):
    __package__ = bootstrap_package()

from .app import App


def main():
    App().main_loop()


if __name__ == "__main__":
    main()
