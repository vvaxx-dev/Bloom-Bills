"""Moss's dialogue: the reusable box, the first-run walkthrough, and the run's beats.

The dialogue layer is deliberately scene-agnostic: any screen can pass a list of
`DialogueStep`s, optionally pointing at a rectangle or a callable that resolves
one against the active scene. Everything else in this module is content for that
layer - the first-run walkthrough, the title-screen guide, and the story beats
Moss plays on the packs screen - so the voice lives in one place and cannot
drift between them. Nothing here changes a number: the mechanical hints live in
`data.py` as the `desc` and `lore` strings on twists, plants, and relics.

Three families of dialogue:

* `intro_steps()` - who you are and why you are holding a watering can. Folded
  onto the front of the first-run packs walkthrough, and shortened on every
  later run so a replay is not punished for remembering.
* `RUN_BEATS` and `SEASON_BEATS` - the arc: the bills, the tenants, the ledger's
  last page. Played once per run and remembered in run.json, because they are
  about *this* attempt at Aunt Marigold's ladder.
* `HAZARD_BEATS` - one warning the first time a twist shows up in a forecast.
  Remembered in profile.json instead, forever: a tip you have already been given
  twice is noise, and Moss only ever explains a rot once.
"""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .settings import ACCENT, CANVAS_H, CANVAS_W, PANEL_DARK

# Moss is a full-height portrait anchored at the bottom-left, Crazy-Dave style.
# The white box sits beside him and still covers about a fifth of the canvas.
# If a highlighted control would be covered by the box, the box lifts just
# enough to keep it visible; if Moss himself would stand over the control, he
# steps to the right edge and the box moves to the left.
BOX_X, BOX_Y, BOX_W, BOX_H = 100, 118, 216, 54
PORTRAIT_GAP = 4
TEXT_PAD = 8
BODY_LINES = 3
LINE_STEP = 7
WHITE = (245, 240, 230)
INK = (32, 27, 50)
FOOT = (106, 110, 132)


def button_rect(button):
    return (button.x, button.y, button.w, button.h)


def _overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


class DialogueStep:
    """One beat of dialogue. `target` may be a rect or a callable(scene)->rect."""

    def __init__(self, text, target=None, speaker="MOSS", portrait="moss"):
        self.text = text
        self.target = target
        self.speaker = speaker
        self.portrait = portrait


class DialogueOverlay:
    """Modal white text box: click/Space advances, Esc skips, arrows highlight UI."""

    def __init__(self, app, steps, on_finish=None, on_skip=None):
        self.app = app
        self.on_finish = on_finish
        self.on_skip = on_skip
        self.t = 0.0
        self.pages = []
        width = BOX_W - TEXT_PAD * 2
        for step in steps:
            lines = gfx.wrap(step.text, width) or [""]
            for i in range(0, len(lines), BODY_LINES):
                self.pages.append((step, lines[i:i + BODY_LINES]))
        if not self.pages:
            self.pages.append((DialogueStep(""), [""]))
        self.index = 0
        self.skip_btn = Button(0, 0, 34, 9, "SKIP", self.skip, color=PANEL_DARK)
        self._place_skip()

    @property
    def step(self):
        return self.pages[self.index][0]

    @property
    def lines(self):
        return self.pages[self.index][1]

    def target_rect(self):
        target = self.step.target
        if callable(target):
            target = target(self.app.scene)
        if not target:
            return None
        try:
            x, y, w, h = (int(v) for v in target)
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return (x, y, w, h)

    def portrait_rect(self):
        """Bottom-anchored Moss; he steps aside if he would cover the target."""
        portrait = gfx.sprite(self.step.portrait)
        w, h = portrait.get_size()
        y = CANVAS_H - h
        left = (0, y, w, h)
        right = (CANVAS_W - w, y, w, h)
        target = self.target_rect()
        if target and _overlaps(left, target) and not _overlaps(right, target):
            return right
        return left

    def box_rect(self):
        px, _py, pw, _ph = self.portrait_rect()
        if px < CANVAS_W // 2:
            x = px + pw + PORTRAIT_GAP
        else:
            x = px - BOX_W - PORTRAIT_GAP
        x = max(0, min(x, CANVAS_W - BOX_W))
        y, w, h = BOX_Y, BOX_W, BOX_H
        target = self.target_rect()
        if target:
            tx, ty, _tw, th = target
            # Keep the highlighted control out from under the white box.
            if ty < y + h and ty + th > y:
                if ty >= y - h:
                    y = max(18, ty - h - 10)
                else:
                    y = min(CANVAS_H - h - 8, ty + th + 10)
        return (x, y, w, h)

    def _place_skip(self):
        x, y, w, h = self.box_rect()
        self.skip_btn.x = x + w - 40
        self.skip_btn.y = y + h - 12

    def update(self, dt):
        self.t += dt

    def advance(self):
        self.index += 1
        if self.index >= len(self.pages):
            self.finish()
        else:
            self._place_skip()

    def back(self):
        if self.index > 0:
            self.index -= 1
            self._place_skip()

    def _close(self, callback):
        self.app.dialogue_modal = None
        if callback:
            callback()

    def finish(self):
        self._close(self.on_finish)

    def skip(self):
        self._close(self.on_skip)

    def on_click(self, pos):
        self._place_skip()
        if self.skip_btn.click(pos):
            return True
        self.advance()
        return True

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
            self.advance()
        elif key == pygame.K_LEFT:
            self.back()
        elif key == pygame.K_ESCAPE:
            self.skip()

    def _draw_arrow(self, surf, box, target):
        tx, ty, tw, th = target
        bx, by, bw, bh = box
        cx = max(bx + 12, min(tx + tw // 2, bx + bw - 12))
        bob = int(self.t * 4) % 2
        if ty + th <= by:
            tip_y = min(ty + th + 2 + bob, by - 5)
            shaft_top, shaft_bottom = tip_y + 4, by - 2
            direction = 1
        elif ty >= by + bh:
            tip_y = max(ty - 2 - bob, by + bh + 4)
            shaft_top, shaft_bottom = by + bh + 2, tip_y - 4
            direction = -1
        else:
            return
        if shaft_bottom >= shaft_top:
            gfx.rect(surf, PANEL_DARK, cx - 2, shaft_top, 4, shaft_bottom - shaft_top + 1)
            gfx.rect(surf, ACCENT, cx - 1, shaft_top, 2, shaft_bottom - shaft_top + 1)
        for row in range(4):
            half = row
            yy = tip_y + direction * row
            gfx.rect(surf, PANEL_DARK, cx - half - 1, yy, half * 2 + 3, 1)
            gfx.rect(surf, ACCENT, cx - half, yy, half * 2 + 1, 1)

    def draw(self, surf, mouse):
        self._place_skip()
        box = self.box_rect()
        target = self.target_rect()
        if target:
            tx, ty, tw, th = target
            for edge in (
                (tx - 2, ty - 2, tw + 4, 1), (tx - 2, ty + th + 1, tw + 4, 1),
                (tx - 2, ty - 1, 1, th + 2), (tx + tw + 1, ty - 1, 1, th + 2),
            ):
                gfx.rect(surf, PANEL_DARK, *edge)
            for edge in (
                (tx - 1, ty - 1, tw + 2, 1), (tx - 1, ty + th, tw + 2, 1),
                (tx - 1, ty, 1, th), (tx + tw, ty, 1, th),
            ):
                gfx.rect(surf, ACCENT, *edge)
            self._draw_arrow(surf, box, target)
        x, y, w, h = box
        portrait = gfx.sprite(self.step.portrait)
        surf.blit(portrait, self.portrait_rect()[:2])
        gfx.panel(surf, x, y, w, h, fill=WHITE, border=PANEL_DARK)
        gfx.rect(surf, ACCENT, x + 1, y + 1, w - 2, 2)
        gfx.draw_text(surf, self.step.speaker, x + TEXT_PAD, y + 5, (46, 120, 62))
        for i, line in enumerate(self.lines):
            gfx.draw_text(surf, line, x + TEXT_PAD, y + 13 + i * LINE_STEP, INK)
        gfx.draw_text(surf, "CLICK / SPACE: NEXT", x + TEXT_PAD, y + h - 8, FOOT)
        gfx.draw_text(surf, "%d/%d" % (self.index + 1, len(self.pages)), x + w - 48, y + h - 8, FOOT, align="right")
        self.skip_btn.draw(surf, mouse)


def _packs_steps():
    from .packs import FORECAST_BOX, GO_BTN, SEED_BOX, SELL_ONE_BTN, SELL_ALL_BTN

    sell_rect = (
        SELL_ONE_BTN[0], SELL_ONE_BTN[1],
        SELL_ALL_BTN[0] + SELL_ALL_BTN[2] - SELL_ONE_BTN[0], SELL_ONE_BTN[3],
    )
    return [
        # The premise is already on the screen by the time this stage starts (see
        # `intro_steps`), so Moss does not reintroduce himself: he gets
        # straight to the one thing a first round needs.
        DialogueStep("SHE LEFT NO MONEY, ONLY SEEDS. THE PACKS ARE FREE THIS ROUND, SO LET'S SEE WHAT THE SHED GAVE US."),
        DialogueStep("OPEN YOUR FREE PACKS HERE. EACH PACK GIVES THREE SEEDS. RARER SEEDS PAY MORE BUT GROW SLOWER.",
                     lambda scene: button_rect(scene.open_btn)),
        DialogueStep("YOUR SEEDS LAND ON THIS SHELF. HOVER ONE TO SEE ITS GROW TIME, HARVEST VALUE AND RESALE PRICE.",
                     SEED_BOX),
        DialogueStep("UNWANTED SEEDS CAN BE SOLD HERE BEFORE THE ROUND. PICK A SEED, THEN SELL 1 OR SELL ALL.",
                     sell_rect),
        DialogueStep("CHECK THE FORECAST. WEATHER CAN SPEED GROWTH, CUT PAYOUTS, OR BAN CERTAIN PLANTS.",
                     FORECAST_BOX),
        DialogueStep("WHEN YOU'RE READY, START THE ROUND. YOU CAN PLANT SEEDS BEFORE THE CLOCK STARTS.",
                     GO_BTN),
    ]


def _round_steps():
    from .round import TRAY_Y, plot_rect

    return [
        DialogueStep("PICK A SEED IN THE TRAY, THEN CLICK AN EMPTY PLOT. PLANT A FEW BEFORE STARTING THE CLOCK.",
                     lambda scene: scene.tray_rect(0) if scene.visible_seeds() else (4, TRAY_Y, 208, 28)),
        DialogueStep("PRESS START OR SPACE WHEN READY. YOU HAVE 45 SECONDS. EVERYTHING LEFT IS SOLD AT THE END.",
                     lambda scene: button_rect(scene.start_btn)),
        DialogueStep("CLICK A GROWING PLANT TO WATER IT: DOUBLE SPEED FOR A FEW SECONDS, THEN A SHORT COOLDOWN.",
                     lambda scene: plot_rect(0)),
        DialogueStep("CLICK A MATURE PLANT TO HARVEST CASH AND START ITS NEXT CYCLE. DON'T LET IT SIT TOO LONG!",
                     lambda scene: plot_rect(0)),
        DialogueStep("THE SHOVEL DIGS UP A CROP WITHOUT RETURNING THE SEED. USE IT TO CLEAR SPACE OR ESCAPE TROUBLE.",
                     lambda scene: button_rect(scene.shovel_btn)),
        # Hazard literacy, taught before the first one can cost anything: the
        # round screen cannot explain a rot it has not rolled yet, so the
        # walkthrough says what the shovel is really for.
        DialogueStep("AND THE SHOVEL IS MEDICINE, TOO. DISEASE, WEEDS, APHIDS - DIG THEM OUT AND THE PLOT COMES BACK CLEAN."),
        DialogueStep("WATCH THE FORECAST. A METEOR CAN TAKE A PLOT OR LEAVE YOU A BETTER ONE, AND STARDUST ONLY WORKS IF YOU PLANT IN IT."),
        DialogueStep("EVERY THIRD ROUND A BILL IS DUE. SAVE ENOUGH TO PAY IT, OR THE RUN ENDS. GOOD LUCK!"),
    ]


def _shop_steps():
    return [
        DialogueStep("SPEND HARVEST CASH ON RELICS. THEIR BONUSES STACK EVERY ROUND, BUT YOU ONLY HAVE FIVE SLOTS.",
                     lambda scene: button_rect(scene.buy_buttons[0]) if scene.buy_buttons else None),
        DialogueStep("BUY PLOTS TO GROW MORE AT ONCE. PRICES CLIMB FAST, SO BALANCE EXPANSION AGAINST RELICS.",
                     lambda scene: button_rect(scene.plot_btn)),
        DialogueStep("REROLL SWAPS THE RELIC OFFERS. IT COSTS CASH, SO SAVE IF YOU'RE HUNTING SOMETHING SPECIFIC.",
                     lambda scene: button_rect(scene.reroll_btn)),
        DialogueStep("NEXT ROUND BRINGS NEW FREE PACKS. KEEP AN EYE ON THE FORECAST AND THE NEXT BILL.",
                     lambda scene: button_rect(scene.next_btn)),
    ]


TUTORIAL_BUILDERS = {"packs": _packs_steps, "round": _round_steps, "shop": _shop_steps}
TUTORIAL_STAGES = tuple(TUTORIAL_BUILDERS)

# The profile key that says "this player has been told why they are gardening".
# `arc-return` is gated on the same key, so the long intro and the short one
# cannot both fire on the same save file.
PREMISE_KEY = "premise"


def tutorial_steps(stage, scene):
    """The steps for one first-run stage, with the premise glued to the front.

    The story is not its own modal on a new run: Moss walks in, explains why you
    are holding a watering can, and keeps talking straight into the walkthrough,
    so there is one thing to click through rather than two.
    """
    builder = TUTORIAL_BUILDERS.get(stage)
    steps = builder() if builder else []
    if stage == "packs" and steps:
        steps = intro_steps(fresh=_first_visit(scene)) + steps
    return steps


def _first_visit(scene):
    """True when this profile has never had the premise read to it before.

    Recorded under its own key in `profile["story_seen"]` rather than inferred
    from "any story has played", so a player who has seen one rot warning still
    gets the full opening on their first run.
    """
    app = getattr(scene, "app", None)
    profile = getattr(app, "profile", None) or {}
    return PREMISE_KEY not in (profile.get("story_seen") or [])


# One line that fits the title screen and says the whole premise. Used there, and
# in the title-screen guide, so the pitch is never two different sentences.
PREMISE = "AUNT MARIGOLD LEFT YOU A GARDEN, A GROUNDSKEEPER, AND EIGHT UNPAID BILLS."

# The returning player's greeting, written once and used twice: as the short
# `intro_steps` and as the round-one beat for a save that has already heard it.
RETURN_LINES = [
    "BACK AGAIN. GOOD. THE GARDEN HOLDS NOTHING AGAINST YOU, AND NEITHER DO I.",
    "HER BILLS, HER SEASONS, HER ROTS. EIGHT PAYMENTS AND THE DEED IS YOURS. MOVE.",
]


def intro_steps(fresh=True):
    """The opening beats, played before the first walkthrough on a new run.

    `fresh` is False once a player has seen the premise before, and the long
    version would just be a wall between them and round one.
    """
    if not fresh:
        return [DialogueStep(text) for text in RETURN_LINES]
    return [
        DialogueStep("MOSS. GROUNDSKEEPER. I WORKED FOR YOUR AUNT THIRTY-SIX YEARS. NOW I APPARENTLY WORK FOR YOU."),
        DialogueStep("THE SHED, THE SOIL AND THE HOUSE ARE YOURS - THE MOMENT THE EIGHT BILLS SHE LEFT YOU ARE PAID. THAT IS THE WILL."),
        DialogueStep("SHE RAN THIS PLACE IN FORTY-FIVE SECOND SLICES AND NEVER ONCE EXPLAINED WHY. JUST HANDED ME THE CAN."),
        DialogueStep("THE GROUND HERE REMEMBERS THINGS. METEORS, ROTS, ONE GHOST IN OCTOBER. SHE PLANTED EVERY BIT OF IT ANYWAY."),
        DialogueStep("YOU HAVE NO TRADE AND NO MONEY, AND THE BANK WANTS THE LOT. SO: PLANT, CUT, SELL, PAY. COME ON."),
    ]


# ---------------------------------------------------------------------------
# The run arc. `rounds` is the set of round numbers a beat may open on, `season`
# means "the first round of that season", and `when` gets the live run so a beat
# can be conditional on what you actually did.
RUN_BEATS = [
    {
        # A returning player never sits through the premise again, but the garden
        # should still notice them: this is the same speech, cut to two lines, and
        # it is why `intro_steps` takes `fresh` at all.
        "id": "arc-return", "rounds": (1,), "requires_seen": PREMISE_KEY,
        "steps": [DialogueStep(text) for text in RETURN_LINES],
    },
    {
        "id": "arc-shed", "rounds": (2,),
        "steps": [
            DialogueStep("THERE'S A NOTE IN THE SEED JAR ON THE KITCHEN STEP. HER HANDWRITING, SO READ IT."),
            DialogueStep("'PLANT BEFORE THE CLOCK, NEVER AFTER.' SHE MEANT THE TRAY, THE PLOTS, AND THE MONEY."),
        ],
    },
    {
        "id": "arc-first-bill", "rounds": (3,),
        "steps": lambda run: [
            DialogueStep(
                "BILL ONE IS DUE WHEN THIS ROUND CLOSES: $%s. SHE NEVER MISSED ONE. SHE ALSO NEVER SAID WHY."
                % fmt(int(run.bill_for_round(run.round)))
            ),
        ],
    },
    {
        "id": "arc-first-paid", "rounds": (4, 5), "when": lambda run: run.quotas_paid >= 1,
        "steps": [
            DialogueStep("ONE BILL DOWN. SHE PAID HER FIRST WITH DAISIES, WHICH IS THE SORT OF STORY SHE'D TELL IF SHE STILL COULD."),
            DialogueStep("THE NEXT IS FIVE TIMES THAT, EVERY THIRD ROUND. THE LADDER IS HER IDEA, NOT MINE."),
        ],
    },
    {
        "id": "arc-shelf", "rounds": (6, 7),
        "steps": [
            DialogueStep("TAKE HER TOOLS TO THE HEIRLOOM SHELF BETWEEN ROUNDS. THEY FOLLOW YOU INTO EVERY GARDEN YOU EVER PLANT AGAIN."),
            DialogueStep("THAT'S HOW SHE BUILT THIS PLACE, IN FACT. ONE BAD SEASON AT A TIME, KEEPING THE GOOD THINGS."),
        ],
    },
    {
        "id": "arc-tenants", "rounds": (9,),
        "steps": [
            DialogueStep("EVERY NINTH ROUND THE VALLEY COLLECTS SOMETHING OF ITS OWN. SHE CALLED THEM HER TENANTS."),
            DialogueStep("SHE COULD NEVER EVICT A SINGLE ONE. SHE JUST PLANTED AROUND THEM AND GOT RICH ANYWAY."),
        ],
    },
    {
        "id": "arc-rows", "rounds": (13, 14),
        "steps": [
            DialogueStep("SHE PLANTED NEIGHBOURS IN PAIRS AND SWEARS THE ROWS TALK. TWO COMPATIBLE CROPS BESIDE EACH OTHER CAN MAKE A THIRD."),
            DialogueStep("NOBODY SELLS THOSE SEEDS. YOU HAVE TO GROW THE PARENTS AND HARVEST ONE OF THEM, AND THAT IS THE WHOLE SECRET."),
        ],
    },
    {
        "id": "arc-deed", "rounds": (24,),
        "steps": [
            DialogueStep("THE LAST BILL. EIGHT PAYMENTS AND THE DEED IS YOURS, AND THE HOUSE STOPS BEING SOMETHING YOU VISIT."),
            DialogueStep("SHE'S IN THERE WITH HER LEDGER, IF YOU WANT TO CALL IT THAT. SO: HEAD UP. SHOVEL DOWN."),
        ],
    },
    {
        "id": "arc-past", "when": lambda run: run.endless and run.round > 24,
        "steps": [
            DialogueStep("PAST THE LAST PAGE OF HER LEDGER NOW. THE BILLS KEEP DOUBLING AND NOBODY HAS TOLD THE VALLEY TO STOP."),
            DialogueStep("SHE FARMED LIKE THIS FOR THIRTY-SIX YEARS AND DIED OWNING NOTHING BUT THE TOOLS. DO BETTER."),
        ],
    },
]

SEASON_BEATS = [
    {"id": "season-spring", "season": "Spring", "steps": [
        DialogueStep("SPRING. THE GROUND SOFTENS AND THE LOW CORNER WETS UP, WHICH IS WHERE THE ROTS START. PLANT SPARSE IF YOU CAN."),
    ]},
    {"id": "season-summer", "season": "Summer", "steps": [
        DialogueStep("SUMMER. LONG DAYS AND THIRSTY SOIL. WATER EARLY, WATER OFTEN, AND NEVER ON A RAIN DAY - THE SKY DOES IT FREE."),
    ]},
    {"id": "season-autumn", "season": "Autumn", "steps": [
        DialogueStep("AUTUMN. SHE LEFT THE GATE OPEN ONE OCTOBER AND SOMETHING WALKED THE ROWS AND SWAPPED TWO CROPS ABOUT."),
        DialogueStep("NOTHING HAPPENED, SHE SAID. SHE STILL WOULD NOT GO OUT AFTER DARK, THOUGH. NOT ONCE."),
    ]},
    {"id": "season-winter", "season": "Winter", "steps": [
        DialogueStep("WINTER. SHORT DAYS, COLD GROUND. SHE SAID: SELL THE SEEDS YOU WON'T PLANT, BECAUSE COAL ISN'T FREE."),
        DialogueStep("AND IF THE FROST COMES WITH IT, THE DESERT CROPS GO IN THE CELLAR OR THEY DIE IN THE BED. HER CHOICE, YOUR MONEY."),
    ]},
]

# ---------------------------------------------------------------------------
# Hazard warnings, keyed to the twist in this round's forecast. Each one is a
# story line with a rule inside it, because Moss refuses to give advice without a
# grudge attached. Shown once per profile.
HAZARD_BEATS = [
    {
        "id": "haz-disease", "twist": "disease",
        "steps": [
            DialogueStep("DISEASE TODAY. IT MOVES PLOT TO PLOT, NEVER AIR TO AIR, SO A SICK CROP IS ONLY DANGEROUS TO ITS NEIGHBOURS."),
            DialogueStep("DIG OUT WHATEVER'S SPOTTED AND LEAVE THE HOLE OPEN. THE SHOVEL IS THE ONLY CURE ON THIS FARM."),
            DialogueStep("SHE LOST THE LOW CORNER THIS WAY. DUSTED IT AFTER, AND NEVER PLANTED A DENSER ROW IN IT AGAIN."),
        ],
    },
    {
        "id": "haz-meteor_shower", "twist": "meteor_shower",
        "steps": [
            DialogueStep("THE SKY'S DUE. TEN SECONDS BETWEEN STRIKES, AND IT PICKS A PLOT, NOT A PLAYER - YOU CAN'T OUT-BUY IT."),
            DialogueStep("IT'LL EITHER TAKE THE CROP OR LEAVE YOU A BETTER ONE. SHE USED TO PLANT STRAIGHT INTO THE CRATERS AND GRIN."),
            DialogueStep("BARE SOIL GETS STARDUST IN IT. PLANT THERE AND THE NEXT CROP COMES OUT STARLIT. THAT'S FREE MONEY IF YOU'RE QUICK."),
        ],
    },
    {
        "id": "haz-weeds", "twist": "weeds",
        "steps": [
            DialogueStep("WEED YEAR. THEY TAKE THE EMPTY PLOTS, AND EVERY ONE STILL STANDING AT THE BUZZER COSTS YOU RENT."),
            DialogueStep("A SHOVEL IS CHEAPER THAN THE BANK. DIG THEM BEFORE THEY SEED THE PLOT NEXT DOOR."),
        ],
    },
    {
        "id": "haz-aphids", "twist": "aphids",
        "steps": [
            DialogueStep("APHIDS. NOTHING SHIFTS THEM BUT A SOAK, AND A SOAK IS HALF YOUR WATERING DAY, SO SPEND IT WHERE IT COUNTS."),
            DialogueStep("SHE SAID THE TRICK WAS NOT TO PANIC AND HARVEST HALFWAY. SHE PANICKED AND HARVESTED HALFWAY."),
        ],
    },
    {
        "id": "haz-blight", "twist": "blight",
        "steps": [
            DialogueStep("BLIGHT. ONE QUITS AT EXACTLY THE MIDDLE OF THE DAY, AND IT PICKS, NOT YOU. SHE CALLED IT THE TAX ON STANDING STILL."),
        ],
    },
    {
        "id": "haz-crow_swarm", "twist": "crow_swarm",
        "steps": [
            DialogueStep("THE FLOCK. SIX SECONDS A BITE, AND THEY EAT WHAT'S RIPEST. A SCARECROW OR AN OWL EARNS ITSELF TODAY, BELIEVE ME."),
        ],
    },
    {
        "id": "haz-hailstorm", "twist": "hailstorm",
        "steps": [
            DialogueStep("HAIL. IT ONLY PUNISHES WHAT'S STILL GROWING, SO CUT EARLY TODAY AND LET NOTHING SIT IN THE BED HALF-RIPENED."),
        ],
    },
    {
        "id": "haz-root_rot", "twist": "root_rot",
        "steps": [
            DialogueStep("ROOT ROT. IT DOESN'T SPREAD AND IT DOESN'T WARN, IT JUST TAKES A PLANT EVERY EIGHT SECONDS. LESSON: MORE PLOTS."),
        ],
    },
    {
        "id": "haz-queen_bee", "twist": "queen_bee",
        "steps": [
            DialogueStep("THE QUEEN'S ROUND. ONLY FLOWERING CROPS PAY HER, AND EVERYTHING ELSE STANDS THERE DORMANT. SHE PLANTED SUNFLOWERS AND SAT."),
        ],
    },
    {
        "id": "haz-ghost", "twist": "ghost",
        "steps": [
            DialogueStep("SHE'S OUT TODAY. SWAPS TWO CROPS AND STARTS BOTH FROM SEED. DON'T CHASE HER - JUST DON'T PLANT ANYTHING EXPENSIVE SIDE BY SIDE."),
        ],
    },
    {
        "id": "haz-eclipse", "twist": "eclipse",
        "steps": [
            DialogueStep("ECLIPSE. THE NIGHT CROPS COME UPSTAIRS FOR THE DAY AND THE SUN-LOVERS SULK. YOUR CELLAR SEEDS GROW UP TOP TODAY, FREE."),
        ],
    },
    {
        "id": "haz-frost", "twist": "frost",
        "steps": [
            DialogueStep("FROST. THE DESERT CROPS WILL DIE IN THE OPEN BED TODAY, SO THEY GO IN THE CELLAR OR THEY WAIT. NOTHING ELSE."),
        ],
    },
    {
        "id": "haz-drought", "twist": "drought",
        "steps": [
            DialogueStep("DROUGHT. EVERYTHING GROWS A THIRD SLOWER, AND WATER STILL DRIES ON SCHEDULE. SO WATER THE CROPS YOU'RE UNSURE ABOUT."),
        ],
    },
    {
        "id": "haz-locusts", "twist": "locusts",
        "steps": [
            DialogueStep("LOCUST YEAR. THEY DON'T TOUCH THE PLANTS, THEY JUST MAKE THE MARKET WORTH LESS. SHE CALLED THAT THE CLEVER VERSION."),
        ],
    },
]





def beat_steps(beat, run):
    """A beat's dialogue, allowing a callable so it can quote live run numbers."""
    steps = beat["steps"]
    return steps(run) if callable(steps) else steps


def beat_seen(profile, beat_id):
    """Whether a once-ever beat has already played for this save file."""
    return beat_id in (profile or {}).get("story_seen", [])


def mark_beat_seen(profile, beat_id):
    """Persist a beat id in profile.json."""
    done = profile.setdefault("story_seen", [])
    if beat_id not in done:
        done.append(beat_id)


def beat_matches(beat, run, profile=None):
    """Whether a beat's own conditions (round, season turn, forecast) are met."""
    require = beat.get("requires_seen")
    if require and not beat_seen(profile, require):
        return False
    rnd = run.round
    if "rounds" in beat and rnd not in beat["rounds"]:
        return False
    if "season" in beat:
        # Season beats land on the first round of the season, not on every round
        # of it, so Moss says each thing about a year exactly once. Round 1 is
        # skipped outright: the opening beats are already talking there.
        if rnd < 2:
            return False
        if not data.is_new_season(rnd) or data.season(rnd)["name"] != beat["season"]:
            return False
    if "twist" in beat and run.twist_id(rnd) != beat["twist"]:
        return False
    when = beat.get("when")
    return not when or bool(when(run))


def beat_due(beat, run, profile=None, persistent=False):
    """Whether this beat is allowed to play right now.

    Arc and season beats are remembered by the run (see `Run.story_beats`), so a
    second attempt at the ladder hears the ledger talk again. Hazard warnings are
    remembered by the save file instead - Moss explains a rot once, ever.
    """
    if not beat_matches(beat, run, profile):
        return False
    if run.story_beat_seen(beat["id"]):
        return False
    return not beat_seen(profile, beat["id"]) if persistent else True


def beat_for(run, profile=None):
    """Return `(beat_id, steps, persistent)` for the beat due now, or None.

    The run arc wins over the hazard warnings: the arc has one or two candidates
    per round, while a forecast beat will still be there next time a rot comes
    back, and the plot it warns about is the same plot either way.
    """
    for beat in RUN_BEATS + SEASON_BEATS:
        if beat_due(beat, run, profile):
            return beat["id"], beat_steps(beat, run), False
    for beat in HAZARD_BEATS:
        if beat_due(beat, run, profile, persistent=True):
            return beat["id"], beat_steps(beat, run), True
    return None


def guide_steps():
    """The premise and the rules, for the title screen and anyone who skipped the intro."""
    return [
        DialogueStep("YOUR AUNT MARIGOLD DIED OWING EIGHT BILLS AND LEAVING YOU THE ONLY THING THAT COULD PAY THEM."),
        DialogueStep("MOSS IS THE GROUNDSKEEPER SHE LEFT BEHIND. HE KNOWS EVERY ROT IN THE SOIL AND WILL EXPLAIN EXACTLY ONE."),
        DialogueStep("OPEN PACKS, PLANT, WATER, CUT, SELL. EVERY THIRD ROUND A BILL IS DUE, AND ONE MISS ENDS THE RUN."),
        DialogueStep("THE VALLEY TAKES A TITHE EVERY NINTH ROUND: CROWS, ROTS, METEORS, A GHOST IN OCTOBER."),
        DialogueStep("PAY THE EIGHTH BILL AT ROUND 24 AND THE DEED IS YOURS. HER TOOLS COME WITH YOU INTO WHATEVER GARDEN YOU TRY NEXT."),
    ]
