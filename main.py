"""Launch the game as either a package module or a direct script."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Plant_Game.app import App


if __name__ == "__main__":
    app = App()
    app.main_loop()
