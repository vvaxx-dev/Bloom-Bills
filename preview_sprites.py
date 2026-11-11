"""Look at sprites from sprites_data.py without starting the game.

    python3 preview_sprites.py                        every sprite on one sheet
    python3 preview_sprites.py daisy my_new_flower    just these
    python3 preview_sprites.py sunflower_gold         a plant or mutant id from data.py, in its recolour
    python3 preview_sprites.py daisy --png daisy.png  write a picture instead of opening a window

The window redraws itself whenever sprites_data.py or data.py is saved, so it
can stay open beside the editor while you draw. G toggles a pixel grid, the
mouse wheel or the arrow keys scroll, Esc closes it.

Every sprite is drawn the two ways the game draws it: at 2x on soil, as on a
plot, and at 1x on a panel, as in the seed tray and the shop. Mistakes that
are easy to make in a text grid are spelled out in red: a row that is too long
or too short, a colour key that is not in PALETTE. A size other than the usual
12x12 is shown in yellow.
"""

import argparse
import difflib
import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

import pygame

if __package__:
    from .settings import ACCENT, BAD, BG, DIM, PANEL, PANEL_DARK, SOIL, SOIL_DARK, START_SCALE, TEXT
else:  # run as a plain script rather than as part of the package
    from settings import ACCENT, BAD, BG, DIM, PANEL, PANEL_DARK, SOIL, SOIL_DARK, START_SCALE, TEXT

FOLDER = Path(__file__).resolve().parent
WATCHED = ("sprites_data.py", "data.py")
STRAY = (255, 0, 255)  # painted wherever the game would crash: a colour key PALETTE lacks, a colour it cannot use
GAP = 16
TEXT_SIZE = 20  # pygame's built-in font spaces its letters evenly at this size


def read(path):
    """Run one of the game's data files and return the names it defines.

    Nothing is imported or cached, so every call sees the file as it is on disk right now.
    """
    scope = {"__name__": path.stem, "__file__": str(path), "__package__": __package__ or ""}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), scope)
    return scope


def load(folder=FOLDER):
    """Read the sprite tables as they stand on disk."""
    sprites, data = (read(Path(folder) / name) for name in WATCHED)
    return SimpleNamespace(
        grids=sprites["GRIDS"], palette=sprites["PALETTE"], plants=data["PLANTS"], relics=data["RELICS"])


def stamp(folder=FOLDER):
    """A fingerprint of the watched files: it changes whenever one of them is saved."""
    marks = []
    for name in WATCHED:
        try:
            stat = os.stat(str(Path(folder) / name))
            marks.append((stat.st_mtime_ns, stat.st_size))
        except OSError:  # an editor may swap the file out for a moment while it saves
            marks.append(None)
    return marks


def explain(exc):
    """A failure in one line: which file and line, and what Python made of it."""
    if isinstance(exc, SyntaxError):
        return "%s, line %s: %s" % (Path(exc.filename or "?").name, exc.lineno, exc.msg)
    if isinstance(exc, OSError):  # a file that could not be read: the message names it
        return "%s: %s" % (type(exc).__name__, exc)
    where = traceback.extract_tb(exc.__traceback__)[-1]
    return "%s, line %s: %s: %s" % (Path(where.filename).name, where.lineno, type(exc).__name__, exc)


def lookup(art, name):
    """The grid and the recolour the game draws for `name`.

    A plant or mutant id from data.py resolves the way a plot does: its own art if it has any, otherwise its
    base plant's, with the mutant's colour swaps. Anything else is taken as a sprite name.
    """
    plant = art.plants.get(name)
    if plant:
        return plant.get("art", plant.get("base", name)), plant.get("subs")
    return name, None


def rows_of(art, grid_name):
    """The rows of a grid that can be drawn, or None if it is missing or is not a list of text rows."""
    grid = art.grids.get(grid_name)
    if isinstance(grid, (list, tuple)) and grid and all(isinstance(row, str) for row in grid):
        return grid
    return None


def paintable(colour):
    """Whether the game could paint with `colour`: it hands pygame the three numbers plus full opacity."""
    try:
        pygame.Surface((1, 1), pygame.SRCALPHA).fill(tuple(colour) + (255,))
        return True
    except (TypeError, ValueError):
        return False


def problems(art, name):
    """What is wrong with the sprite drawn for `name`, in plain words. An empty list means nothing is."""
    grid_name, swaps = lookup(art, name)
    if grid_name not in art.grids:
        drawable = set(art.grids) | {plant for plant in art.plants if lookup(art, plant)[0] in art.grids}
        close = difflib.get_close_matches(grid_name, sorted(drawable), 3)
        hint = " - did you mean %s?" % " or ".join(close) if close else ""
        return ["there is no sprite called %r%s" % (grid_name, hint)]
    rows = rows_of(art, grid_name)
    if rows is None:
        return ["is not a list of text rows"]
    colours = dict(art.palette, **(swaps or {}))
    widths = [len(row) for row in rows]
    usual = max(sorted(set(widths)), key=widths.count)
    found = []
    for number, row in enumerate(rows, 1):
        if len(row) != usual:
            joined = usual and len(row) > usual and len(row) % usual == 0
            found.append("row %d is %d wide, the others are %d%s" % (
                number, len(row), usual, " - is a comma missing at the end of a line?" if joined else ""))
        strays = sorted(set(row) - set(colours) - {"."})
        if strays:
            found.append("row %d uses %s, which PALETTE does not have - the game would crash drawing it" % (
                number, " and ".join(repr(key) for key in strays)))
    for key in sorted(set("".join(rows)) & set(colours)):
        if not paintable(colours[key]):
            found.append("uses %r, but its colour is %r, not three numbers from 0 to 255 - "
                         "the game would crash drawing it" % (key, colours[key]))
    in_game = set(art.relics) | {lookup(art, plant)[0] for plant in art.plants}
    if not found and grid_name in in_game and (usual, len(rows)) != (12, 12):
        found.append("is %dx%d, but plant and relic sprites have to be 12x12" % (usual, len(rows)))
    return found


def report(art, names, error=""):
    """Every message for the artist: a file that would not load first, then each sprite's problems."""
    return ([error] if error else []) + ["%s: %s" % (name, said) for name in names for said in problems(art, name)]


def render(art, name, scale):
    """Draw the sprite for `name` exactly as gfx.sprite() would, with STRAY wherever the game would crash."""
    grid_name, swaps = lookup(art, name)
    rows = rows_of(art, grid_name) or rows_of(art, "unknown") or ["."]
    colours = dict(art.palette, **(swaps or {}))
    surf = pygame.Surface((len(rows[0]) * scale, len(rows) * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, key in enumerate(row):
            if key != ".":
                cell = (x * scale, y * scale, scale, scale)
                try:
                    surf.fill(tuple(colours[key]) + (255,), cell)
                except (KeyError, TypeError, ValueError):
                    surf.fill(STRAY, cell)
    return surf


def wrap(text, face, width):
    """Split `text` into lines no wider than `width` pixels in the font `face`."""
    lines, line = [], ""
    for word in text.split():
        trial = word if not line else line + " " + word
        if line and face.size(trial)[0] > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def tile(picture, scale, edge, fill):
    """A framed patch of background with `picture` on it, one game pixel clear of the frame."""
    w, h = picture.get_width() + 4 * scale, picture.get_height() + 4 * scale
    surf = pygame.Surface((w, h))
    surf.fill(edge)
    surf.fill(fill, (scale, scale, w - 2 * scale, h - 2 * scale))
    surf.blit(picture, (2 * scale, 2 * scale))
    return surf


def card(art, name, scale, face, grid=False):
    """One sprite: its name and size, then the 2x soil view and the 1x panel view side by side."""
    grid_name, swaps = lookup(art, name)
    plot = tile(render(art, name, 2 * scale), scale, SOIL_DARK, SOIL)
    icon = tile(render(art, name, scale), scale, PANEL_DARK, PANEL)
    if grid:
        step = edge = 2 * scale
        lines = pygame.Surface(plot.get_size(), pygame.SRCALPHA)
        for x in range(edge, plot.get_width() - edge + 1, step):
            pygame.draw.line(lines, (0, 0, 0, 90), (x, edge), (x, plot.get_height() - edge))
        for y in range(edge, plot.get_height() - edge + 1, step):
            pygame.draw.line(lines, (0, 0, 0, 90), (edge, y), (plot.get_width() - edge, y))
        plot.blit(lines, (0, 0))
    rows = rows_of(art, grid_name)
    size = (len(rows[0]), len(rows)) if rows else None
    title = face.render(name, True, BAD if problems(art, name) else TEXT)
    shape = face.render("%dx%d" % size if size else "?", True, DIM if size == (12, 12) else ACCENT)
    source = ([grid_name] if grid_name != name else []) + (["recoloured"] if swaps else [])
    detail = face.render("  ".join([""] + source), True, DIM)
    top = title.get_height() + shape.get_height() + 6
    views = plot.get_width() + 2 * scale + icon.get_width()
    width = max(views, title.get_width(), shape.get_width() + detail.get_width())
    surf = pygame.Surface((width, top + plot.get_height()))
    surf.fill(BG)
    surf.blit(title, (0, 0))
    surf.blit(shape, (0, title.get_height() + 2))
    surf.blit(detail, (shape.get_width(), title.get_height() + 2))
    surf.blit(plot, (0, top))
    surf.blit(icon, (plot.get_width() + 2 * scale, top))
    return surf


def compose(art, names, scale, width, grid=False, error=""):
    """The whole picture: anything wrong in red at the top, then a card per sprite, as many across as fit `width`."""
    pygame.font.init()
    face = pygame.font.Font(None, TEXT_SIZE)
    cards = [card(art, name, scale, face, grid) for name in names]
    cell_w = max([c.get_width() for c in cards] + [0]) + GAP
    cell_h = max([c.get_height() for c in cards] + [0]) + GAP
    across = max(1, min(len(cards), (width - GAP) // cell_w))
    lines = [line for said in report(art, names, error) for line in wrap(said, face, width - 2 * GAP)]
    line_h = face.get_linesize()
    top = GAP + (len(lines) * line_h + GAP if lines else 0)
    sheet_w = max([across * cell_w - GAP] + [face.size(line)[0] for line in lines]) + 2 * GAP
    surf = pygame.Surface((sheet_w, top + -(-len(cards) // across) * cell_h))
    surf.fill(BG)
    for i, line in enumerate(lines):
        surf.blit(face.render(line, True, BAD), (GAP, GAP + i * line_h))
    for i, one in enumerate(cards):
        surf.blit(one, (GAP + (i % across) * cell_w, top + (i // across) * cell_h))
    return surf


class Preview:
    """The sprites being looked at, kept in step with the files on disk."""

    def __init__(self, names=(), scale=None, folder=FOLDER):
        self.folder, self.names = Path(folder), list(names)
        self.scale = max(1, scale or (START_SCALE if 0 < len(self.names) <= 8 else 3))
        self.grid, self.error = False, ""
        self.seen, self.settling = stamp(self.folder), None
        self.art = self.fresh()

    def fresh(self):
        """The tables as they are on disk now, once it is certain they can be drawn."""
        art = load(self.folder)
        compose(art, self.names or list(art.grids), self.scale, 400)
        return art

    def shown(self):
        """The names on the sheet: the ones asked for, or every sprite there is."""
        return self.names or list(self.art.grids)

    def update(self):
        """Read the files again once a save has settled. True when that leaves the picture out of date."""
        now = stamp(self.folder)
        if now == self.seen:
            return False
        if now != self.settling:  # an editor empties a file before rewriting it: wait for two looks to agree
            self.settling = now
            return False
        try:
            art, error = self.fresh(), ""
        except Exception as exc:  # a half-typed edit must not close the window
            art, error = self.art, "%s - still showing the last version that loaded" % explain(exc)
            if isinstance(exc, OSError):  # the file could not be read this time: leave it to be tried again
                now = self.settling = None
        stale = (art, error) != (self.art, self.error)
        self.art, self.error, self.seen = art, error, now
        return stale

    def messages(self):
        return report(self.art, self.shown(), self.error)

    def picture(self, width=1280):
        return compose(self.art, self.shown(), self.scale, width, self.grid, self.error)


def watch(preview):
    """Show the picture in a window and keep it in step with the files until the window is closed."""
    pygame.display.init()
    desk_w, desk_h = (pygame.display.get_desktop_sizes() or [(1280, 800)])[0]
    picture = preview.picture(max(420, desk_w - 80))
    roomy = (max(picture.get_width(), 420), min(picture.get_height() + 100, desk_h - 120))  # room for red lines
    screen = pygame.display.set_mode(roomy, pygame.RESIZABLE)
    pygame.display.set_caption("Sprite preview - redraws when sprites_data.py is saved - G: pixel grid, Esc: close")
    clock, scroll, fitted = pygame.time.Clock(), 0, screen.get_width()
    while True:
        stale = preview.update()
        for event in pygame.event.get():
            key = event.key if event.type == pygame.KEYDOWN else None
            if event.type == pygame.QUIT or key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.display.quit()
                return
            if key == pygame.K_g:
                preview.grid, stale = not preview.grid, True
            if event.type == pygame.MOUSEWHEEL:
                scroll -= 60 * event.y
            scroll += {pygame.K_DOWN: 60, pygame.K_UP: -60, pygame.K_PAGEDOWN: 600, pygame.K_PAGEUP: -600}.get(key, 0)
        screen = pygame.display.get_surface()
        if stale or screen.get_width() != fitted:
            fitted = screen.get_width()
            picture = preview.picture(fitted)
        scroll = max(0, min(scroll, picture.get_height() - screen.get_height()))
        screen.fill(BG)
        screen.blit(picture, (0, -scroll))
        pygame.display.flip()
        clock.tick(30)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", metavar="NAME",
                        help="a sprite name from sprites_data.py, or a plant or mutant id from data.py "
                             "(default: every sprite)")
    parser.add_argument("--png", metavar="FILE",
                        help="write the picture to FILE and exit, without opening a window "
                             "(exit status 1 if a sprite has something wrong with it)")
    parser.add_argument("--scale", type=int, metavar="N",
                        help="screen pixels per game pixel (default: %d, as the game window starts out, "
                             "or 3 for a sheet of more than eight sprites)" % START_SCALE)
    args = parser.parse_args(argv)
    try:
        preview = Preview(args.names, args.scale)
    except Exception as exc:
        print(explain(exc), file=sys.stderr)
        return 1
    if not args.png:
        watch(preview)
        return 0
    target = Path(args.png)
    if target.suffix.lower() != ".png":
        target = target.with_name(target.name + ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(preview.picture(), str(target))
    print("wrote %s" % target)
    for said in preview.messages():
        print(said, file=sys.stderr)
    return 1 if preview.messages() else 0


if __name__ == "__main__":
    sys.exit(main())