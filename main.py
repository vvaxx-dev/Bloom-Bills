"""Launch the game as either a package module or a direct script."""

import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
if __package__ in (None, ""):
    parent = root.parent
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    pkg_name = root.name.replace("-", "_")
    if pkg_name:
        spec = importlib.util.spec_from_file_location(pkg_name, root / "__init__.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = module
        module.__path__ = [str(root)]
        module.__package__ = pkg_name
        module.__spec__ = spec
        module.__file__ = str(root / "__init__.py")
    __package__ = pkg_name

from .app import App


if __name__ == "__main__":
    app = App()
    app.main_loop()
