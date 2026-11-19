# Bloom & Bills

A compact gardening economy game: grow crops against a clock, pay eight escalating bills, and carry permanent heirlooms into future runs.

## At a glance

| System | Current value |
| --- | --- |
| Canvas | 320×180 internal resolution, integer-scaled 6× by default; 2×–8× in Settings, borderless by default |
| Runtime | About 16,500 lines of Python across 29 files (including four test modules and a sprite preview tool); one runtime dependency: `pygame-ce>=2.5` |
| Round clock | 45 seconds for rounds 1–3; the base drops 2 seconds per round from round 4 to a 30-second floor, then weather/relics can add or remove time, with a 10-second minimum |
| Starting position | $15, 4 surface plots, and 2 free packs of 3 seeds each |
| Bills | Rounds 3, 6, 9 … 24; `300 × 5^(bill-1)`, so the eighth is **$23,437,500** |
| Win | Pay the eighth bill at round 24, then retire with the deed or continue into endless mode |
| Content | 25 base plants, 12 crossbreeds, 35 mutant forms, 8 seed packs, 27 relics, 8 heirlooms, 23 weather twists including 10 bosses, and 12 relic/plant pairings |

## Quick start

```sh
pip install -r requirements.txt
python3 main.py
```

`main.py` bootstraps the hyphenated repository directory when run as a plain script; tools and tests can import the package as `Bloom-Bills` from the parent directory.

## Saves, settings, and debug keys

`save.py` writes two JSON files with atomic temp-file replacement:

- `profile.json` — banked heirlooms, purchased perk levels, best round, settings, harvest milestones, discovered crossbreeds, and completed tutorial stages.
- `run.json` — the active run snapshot, including RNG state so forecasts stay stable after a reload, plus any crossbreeds discovered this run (merged into `profile.json` when the run ends, and written there the moment one drops).

`paths.py` resolves the save directory as:

- Windows: `%APPDATA%/BloomAndBills`
- macOS: `~/Library/Application Support/BloomAndBills`
- Linux/other: `$XDG_DATA_HOME/BloomAndBills`, defaulting to `~/.local/share/BloomAndBills`
- Override any of these with `BLOOM_SAVE_DIR=/some/path`.

Settings persist in `profile.json`. Defaults are `confirmations: true`, `floaters: true`, `auto_harvest: false`, and `scale: 6` (clamped to 2–8). **Auto Harvest** collects the instant a crop matures; **Floating Text** controls harvest/payout floaters; **Confirm Prompts** controls destructive confirmations. F11 toggles fullscreen, F12 toggles borderless mode.

With `BLOOM_DEBUG=1`, F2 toggles 10× round speed and F3 adds $10,000. These keys are ignored in normal play.

## A round, start to finish

Each round starts on the **packs screen**. Two free packs are granted by default, each with a type drawn from a weighted pool of packs already unlocked by your round number; opening one yields three seeds from that pack's own weighted seed pool. Garden Pack weight tapers down as better packs unlock; the **Seed Stash** heirloom and **Seed Catalog** relic can add more free packs. Buying a pack costs its base price multiplied by `1.5^(round-1)`.

Click a seed, then click an empty plot. You can plant before or during the clock; press **START** or **Space** to start the timer. The round screen shows six seeds per tray page and pages with the arrows, Left/Right, or the mouse wheel. During an Eclipse or Eternal Night, owned nocturnal seeds join the surface tray.

Plants grow on their own. Clicking a growing surface plot waters it: base watering lasts **4.5 seconds**, doubles growth while active, and the soil then needs **3 seconds** to recover. Perfectly timed watering therefore gives double speed for 4.5 out of every 7.5 seconds, before relics such as Big Can change the timing. You start with four surface plots and can buy up to twelve; the first extra plot costs $200 and each further plot costs 3× the previous one.

Harvesting is manual by default: click a mature plant on either board to collect its payout and start another growth cycle. Mature plants wait until harvested or sold at round end. Enable **Auto Harvest** to collect immediately instead. A Daisy has a 5-second base growth cycle and pays $2; Golden Orchid takes 28 seconds and pays $300. At the end of the round, every planted crop is liquidated for `int(sell × min(1, progress / grow) × sale multipliers)`; Compost Heap and Stock Market can raise those multipliers. Each payout is truncated to whole dollars, then the plots are cleared.

Four twists put hazards on the plots themselves rather than on the round's multipliers, and they are the reason to keep the shovel selected: a sick crop is cured only by digging it out, a weed patch refuses new seed until it is dug, an aphid colony washes off with a single watering, and a meteor strike either empties a plot or leaves it starlit at ×1.5. The round banner reports what the hazard has actually done this round, and hovering the forecast repeats the rule. See **Garden hazards** below.

Unplanted seeds are sold on the packs screen, not mid-round. The seed shelf is clickable; **SELL 1** and **SELL ALL** use `max(1, 25% of the plant's sell value)`, so a Daisy seed is $1 and a Golden Orchid seed is $125. The round tray's tooltip still shows resale value and points back to the packs screen.

The packs screen has three paged shelves: unopened packs (12 per page), owned seeds (8 per page, with the resale strip), and packs for sale (4 per page). Left/Right, Up/Down, and the mouse wheel page the relevant shelf; hovering a pack shows its weighted contents and odds. The round screen's forecast and banner use compact weather lines measured against the 320px canvas, so long descriptions do not paint off screen.

## The bill ladder

A bill is due after every third round. Round 3 is deterministic Fair Weather; later non-boss quota rounds draw from `RANDOM_TWISTS`. The first eight bills are:

`300, 1,500, 7,500, 37,500, 187,500, 937,500, 4,687,500, 23,437,500`.

The post-round summary asks you to pay the bill explicitly. If you cannot afford it, the **PAY $…** button is disabled unless you have an unused **Old Insurance Card** waiver; the button then reads **USE WAIVER** instead. The **DON'T PAY** button ends the run, with a confirmation if you could have afforded the bill. After the eighth bill, endless mode multiplies each subsequent bill by 6, still every third round.

## Weather, bosses, and seasons

Weather is deterministic from the run seed and round number, so a forecast never changes after a reload. Round 1 is Fair Weather. From round 9 onward, every ninth round is a boss round, which takes priority over quota weather. Quota rounds after the first draw from `RANDOM_TWISTS`; other non-boss, non-quota rounds are Fair Weather 60% of the time and otherwise draw one of five minor twists.

| Ordinary twist | Effect |
| --- | --- |
| Fair Weather / Dead Calm | No numeric change |
| Sunny Day | +25% growth |
| Rain | Surface plots water themselves all round |
| Market Day | +25% harvest value |
| Eclipse | Nocturnal seeds can be planted on the surface; nocturnal crops grow 30% faster and all other surface crops 20% slower |
| Drought | −35% growth |
| Locusts | −40% harvest value |
| Short Days | −20 seconds from the round |
| Frost | Desert-tagged seeds cannot be planted on the surface |
| Blight | One random surface plant withers at halfway |
| Weeds | Every 12 seconds an empty surface plot sprouts weeds; weeds block planting and cost $6 each at the buzzer |
| Aphids | Every 7 seconds a colony settles on one surface crop and halves its harvest; watering that plot washes them off |

Every twist has a short HUD line. Banners, forecasts, toasts, and tooltips measure, wrap, hard-break, or trim text to the canvas; toasts are capped at two lines and tooltips are clamped to the screen.

| Boss (every ninth round) | Effect |
| --- | --- |
| Crazy Crows! | Every 6 seconds, eats one random surface plant. Mutants have 0.8 weight, so they are 20% less likely to be chosen |
| Hailstorm | Every 7 seconds, halves the growth of each still-growing surface plant. Mature plants are unaffected |
| The Garden Ghost | Autumn only; every 5 seconds swaps two surface plants and restarts both from seed |
| Queen Bee | Only plants with the `flower` tag grow or harvest on the surface; other surface plants are dormant |
| Root Rot | Every 8 seconds, removes one random surface plant |
| Heatwave | −15% growth; surface watering dries twice as fast |
| Eternal Night | Applies Eclipse planting and growth rules for the whole round |
| Gale | −10 seconds and −20% growth |

### Garden hazards

Four twists mark the soil instead of retuning the whole round, so they are read off the plots rather than off a multiplier. They are ordinary twists and bosses like any other weather: `weeds` and `aphids` ride in `RANDOM_TWISTS`, while `disease` and `meteor_shower` sit at the end of `BOSS_TWISTS` so that every round number keeps the boss it already had. All four are **surface-only** — the cellar never infects, never weeds up, and is never struck, which is part of what buying that land means.

| Hazard | Cadence | What lands on the plot | The answer |
| --- | --- | --- | --- |
| Disease | one new case every 15s, spread rolls every 6s | growth ×0.55, harvest ×0.6, sale ×0.6; each sick crop can infect a *planted* neighbour | the shovel: digging a sick crop clears the plot to bare, uninfected soil |
| Meteor Shower | one strike every 10s | 45% chance the plot is flattened outright, otherwise the crop is rewritten as a mutation and turns **starlit** | `starlit` multiplies harvest and sale by **1.5 after all other maths**; a strike on bare soil leaves stardust for your next seed there |
| Weeds | every 12s | an empty plot is taken; 45% of the time it instead seeds a neighbour of an existing weed | dig it out (no confirmation, no cost) or pay $6 per patch at the buzzer; planting is refused until the soil is clear |
| Aphids | every 7s | one crop's harvest is halved and its end-of-round sale is ×0.7 | water the plot — any watering, including Rain and the Hired Gardener, washes the colony off |

Disease spreads plot-to-plot and never across a gap, and each sick plot rolls **once** per contagion tick against a single random neighbour, so one case cannot cascade down a row in one frame. Sulphur Duster softens all three disease penalties by `sick_relief` and halves the spread chance; Lightning Rod removes the meteor's destroy branch, leaving only the upside. Weeds and stardust both live on *empty* plots, so they compete: a meteor that lands on a weedy plot burns the weed and leaves nothing behind.

Most boss events are surface-only; global time changes still affect the run. A season lasts nine rounds: rounds 1–9 are Spring, 10–18 Summer, 19–27 Autumn, 28–36 Winter, then the cycle repeats. Each season has a topbar tint and pixel-art emblem; Autumn leaves and Winter snow are visual effects. Seasons are mostly cosmetic, except that the Garden Ghost is restricted to Autumn.

## Seeds and packs

There are 25 base plants, 35 mutant forms, and 8 packs. Pack prices below are base prices before the `1.5^(round-1)` multiplier.

| Pack | Unlock | Base price | Pool highlights |
| --- | ---: | ---: | --- |
| Garden | 1 | $30 | Daisy, Tomato, Sunflower, Venus Flytrap, Mycelium, and about 1% Golden Orchid |
| Farmer | 2 | $120 | Potato, Wheat, Carrot, Corn, Cranberries, Saffron |
| Nocturnal | 2 | $120 | Brown/Red Mushroom, Mycelium, Moonflower, Queen of the Night |
| Harvest | 3 | $100 | Pumpkin, Corn, Cranberries, Wheat, Potato, Carrot |
| Rare | 4 | $400 | Sunflower, Cactus, Pumpkin, Four-Leaf Clover, Golden Orchid, Crystal Bloom; 2.5× weighting for rare/legendary seeds |
| Desert | 6 | $250 | Cactus, Aloe Vera, Prickly Pear, Agave |
| Cursed | 6 | $600 | Devil's Ivy, Widow's Bloom, Moonflower, Queen of the Night |
| Golden | 9 | $750 | Pumpkin, Cactus, Golden Orchid |

Crystal Bloom appears only in Rare Packs. Golden Orchid appears in Garden, Golden, and Rare Packs. Every pool is weighted; the packs screen shows the rounded percentages for each seed. Seed pools, the seed shelf, and the round tray are all listed in rarity order (common → uncommon → rare → legendary → exquisite, then name).

## Plants with special rules

- **Mutations.** Once a plot reaches its threshold of 2–5 harvests, depending on the base grow time, every harvest from then on has a 10% chance to mutate. Mutant yield/sell multipliers range from 1.8× to 4× and grow-time multipliers from 0.7× to 1.7×; some mutants also add flat harvest bonuses. Golden Sunflower triples value but takes 50% longer to grow. Mycelium and Crystal Bloom never mutate; the other 23 base plants have at least one mutant form. Mutagen gives seeds a 25% chance to sprout already mutated and adds 20% to mutant harvest multipliers. Cursed mutations retain upkeep and auras.
- **Cursed plants.** Devil's Ivy pays well and charges $60 upkeep at the end of each round. Widow's Bloom halves every non-cursed harvest on either board while it is planted.
- **The cellar.** A $250 shop unlock adds four plots. It accepts nocturnal plants and fungi, so Mycelium can be planted either upstairs or below. Cellar crops grow at 0.75× speed without watering and are spared most surface-only boss effects, but they still need harvesting unless Auto Harvest is enabled.
- **Mycelium.** Connected Mycelium forms one patch; each extra member adds 12% to the whole patch's harvest multiplier. Harvesting any Mycelium in the patch has a 1-in-20 chance to spread into an empty orthogonal plot, and a shared creep meter guarantees another spread every 20 seconds of active round time while there is somewhere to go. Each board's mycelium expansion is capped at three new plots per round, and the front grows from the patch's outer edge so harvesting the original plot never stalls it.
- **Venus Flytrap.** Pays little on its own, but each harvest of another crop on either board adds $2 to each Flytrap's next bite. An ambient critter wandering near a Flytrap adds $3 to that Flytrap's next base harvest, with a short cooldown. Its Man-Eater mutation eats one orthogonal neighbour before it is paid and keeps half that plant's base yield.
- **Four-Leaf Clover.** Pays nothing itself. Each harvest of the clover has a 25% chance to multiply one neighbouring paying plant's base harvest by 1.5 for the rest of the round. Its only mutation, Five-Leaf Clover, uses a 50% chance for 2× instead.
- **Crystal Bloom.** A slow legendary Rare Pack seed. Once mature, each full second left unharvested adds $20 to its next harvest before multipliers. Auto Harvest collects immediately, so it cannot build this bonus; end-of-round sales use the ordinary partial-progress formula instead.
- **Crossbreeding.** Twelve seeds are sold by no pack. When two parent plants grow in orthogonally adjacent plots (above, below, left or right — the cellar plot directly below a surface plot also counts), harvesting either parent rolls a recipe chance (8–20%) to drop one child seed into the shelf; there is no per-round cap, so a pair can be harvested repeatedly while its condition holds. Ordinary recipes accept a parent in any form (a Golden Sunflower still counts as a Sunflower); the Eclipse Sovereign demands the exact Golden Sunflower + Blood Moonflower mutants under an eclipse and takes precedence over the ordinary Eclipse Bloom. Crossbreeds never mutate further.

| Crossbreed | Parents (adjacent) | Condition | Grow / Yield | Inherited twist |
| --- | --- | --- | --- | --- |
| Eclipse Bloom | Sunflower + Moonflower | Eclipse | 15s / $150 | Sun-and-moon flower: cellar or eclipse-top, races in the dark |
| Rainbow Daisy | Daisy + Four-Leaf Clover | Rain | 9s / $45 | Pays, and 25% of harvests ×1.5 a neighbour |
| Solar Saffron | Saffron + Sunflower | Sunny Day | 24s / $320 | A further +25% growth in sunshine |
| Spiny Pumpkin | Cactus + Pumpkin | Drought or Heatwave | 22s / $220 | Treats drought and heatwaves as fair sun (×1.25) |
| Frost Tomato | Tomato + Cranberries | Frost | 16s / $110 | Winter-hardy: plantable during Frost |
| Ghost Bloom | Pumpkin + Moonflower | Autumn | 18s / $200 | +25% growth in Autumn; the Moonflower may haunt from the cellar below |
| Man-Eater Tomato | Venus Flytrap + Tomato | Any | 14s / $90 | Eats a neighbour per harvest, is fed $2 by harvests, snaps critters |
| Lucky Orchid | Four-Leaf Clover + Golden Orchid | Any | 28s / $380 | 25% of harvests ×1.5 a neighbour |
| Prism Bloom | Crystal Bloom + Golden Orchid | Any | 30s / $450 | +$30 per full second mature — Auto Harvest starves it |
| Snap Aloe | Aloe Vera + Venus Flytrap | Any | 15s / $70 | Fed $2 by every harvest anywhere, critters included |
| Desert Bloom | Prickly Pear + Agave | Any | 26s / $350 | Desert, fruit and flower at once: feeds both pairing families |
| Eclipse Sovereign | Golden Sunflower + Blood Moonflower (exact mutants) | Eclipse | 18s / $600 | The crowned chase seed |

Ambient critters visit in groups of at most three. They crawl, hop, or fly off screen, stay away briefly, and re-enter from another garden edge. They are decorative except when a Venus Flytrap eats one. The Eternal Snail relic adds a separate violet cursor-chaser that ends the run if it catches the mouse after its grace period.

## Relics

There are 27 relics, each with a 12×12 pixel-art badge. Five slots are available by default; **Relic Cabinet** level 2 gives a sixth. The shop shows three offers by default and four at Relic Cabinet level 3. Rerolling starts at $50, doubles after each reroll in the same shop, and scales with `1.3^(round-1)`.

Relic prices use a base cost, a rarity multiplier (common 1.0, uncommon 1.2, rare 1.45, legendary 1.6, exquisite 1.8), and per-round growth: 1.35× for rare and exquisite relics, 1.3× for the others. Packs rise 1.5× per round, plots triple with each purchase, and bills climb 5× every three rounds (about 1.71× per round) through the eighth bill. Owned relic effects stack for the run, some evolve when their counters reach a goal, and a relic can be sold back for half the price paid for it.

Examples include Monoculture's 2.5× payout for a single-species garden, Biodiversity's +20% harvest per distinct species, Beehive's adjacent-flower bonus, Scarecrow's 1.5× harvests, and Greenhouse's 2× harvests plus 10% growth.

| Relic | Effect |
| --- | --- |
| Time Capsule | Every 10 seconds, pays out 25% of the harvest cash earned in the previous 10 seconds |
| Stock Market | Picks one species from your seeds or planted crops when the clock starts and doubles that species' end-of-round sale |
| The Collector | Makes scalable relic effects 2% stronger for each distinct species planted |
| Emergency Generator | During bad-weather twists, multiplies the weather growth factor by 1.2 on both boards, softening a 35% drought penalty to 22% |
| The Friendly Owl | Scares off crows and drops a bonus seed every 12 seconds |
| Clear Skies | 50% chance at halfway to clear the current weather or boss for the rest of the round, even if it was beneficial; the starting round duration stays fixed and effects that already happened are not undone |
| Chosen Bloom | Click its name in the relic panel, then choose one planted plot on either board each round: that plant grows 50% faster and harvests for 2×. The choice is spent even if the plant is removed or destroyed |
| Eternal Snail | All plants grow 30% faster, but a violet snail follows the cursor and ends the run if it catches you |

### Plant pairings

Twelve relics have a **plant pairing**; the table mirrors the game's own pairing labels. Requirements are counted from currently planted surface and cellar plots, so a pairing turns on and off as the garden changes. `distinct` means unique species, not plot count. Where "power" is mentioned, the relic's scalable numeric effects are amplified; boolean effects such as crow protection or weather clearing are unchanged.

| Relic | Requirement | While active |
| --- | --- | --- |
| Green Thumb | 4+ flowers | Flowers +5% growth; Green Thumb +10% power |
| Beehive | 5+ flowers | Flowers +5% growth and +5% harvest; Beehive +10% power |
| Desert Rose | 4+ desert crops | Those crops +8% growth; Desert Rose +10% power |
| Spore Lantern | 4+ mushrooms | Mushrooms +8% growth and +5% harvest; Spore Lantern +10% power |
| Scarecrow | 4+ vegetables | Vegetables +5% growth; Scarecrow +10% power |
| Monoculture | 4+ plots, all one species | That crop +6% growth; Monoculture +10% power |
| Biodiversity | 6+ distinct species | All crops +4% growth and +3% harvest; Biodiversity +10% power |
| Mutagen | 2+ mutants | Mutants +8% growth; Mutagen +10% power |
| Clear Skies | Eclipse or Eternal Night, plus 3+ nocturnal crops | Nocturnal crops +10% growth |
| The Friendly Owl | 2+ carnivores | Carnivores +8% harvest; the owl drops double seeds |
| The Collector | 5+ distinct species | All crops +3% growth; all relics +5% power |
| Stock Market | 3+ rare or legendary crops | Rare/legendary species weigh 10% more in the stock pick |

The Garden Index lists each exact requirement. Shop and round tooltips show the same pairing line, and the round tooltip marks a live pairing with `PAIRING ACTIVE!`.

## Heirlooms

Heirlooms are permanent meta-progression currency, not cash. The run-end reward is `max(0, round — 1) + 3 × bills_paid`, plus 10 for a win. Spend them at the **Heirloom Shelf**; levels and banked totals live in `profile.json`. Upgrade costs come from each perk's cost list multiplied by `1.15^level`, and the shelf and pause panel page five rows at a time.

| Heirloom | Levels | Effect |
| --- | ---: | --- |
| Deep Pockets | 10 | +2% end-of-round cash interest per level through level 9, then 25% at level 10; stacks with Piggy Bank |
| Spare Plot | 4 | +1 starting surface plot per level |
| Seed Stash | 2 | +1 free pack per round per level |
| Green Thumbs | 10 | +10% to every harvest per level |
| Relic Cabinet | 3 | Level 1: 15% off relics. Level 2: a sixth owned relic slot. Level 3: a fourth shop offer |
| Lucky Penny | 3 | After a paid bill, 8% chance per level that one live relic offer is free; rerolling clears the free offer |
| Antique Clock | 3 | +2 seconds of free growth per level at the start of each timed round |
| Old Insurance Card | 1 | One bill per run is waived instead of paid when cash is short |

Every heirloom has its own 12×12 pixel-art badge and lore entry. All effects carry into future runs.

## Garden Index and interface

The **Garden Index** has two top sections, **Plants** and **Upgrades**. Plants has **ALL**, **GARDEN**, **DESERT**, **FARMER**, **NIGHT**, **MUTANTS**, and **CROSSBREEDS** subsections; Upgrades has **RELICS** and **HEIRLOOMS**. Entries are shown in a 3×3 grid, nine per page, and every catalogue — plants, mutants (by base rarity), crossbreeds, relics, pack pools, the seed shelf, the round tray, and the owned-relic rows — is ordered by rarity first, then name. Left/Right or the wheel pages, Up/Down cycles subsections, and Tab switches Plants/Upgrades. The Index opens from the title screen and from the in-game **pause menu** (Esc → **GARDEN INDEX**); closing it returns to the paused round exactly as it was left.

Relic pages show artwork, price, description, ownership, evolution goals, and plant-pairing requirements. Heirloom pages show artwork, permanent level, current and next bonuses, cost, and lore. The index covers all 27 relics, all 8 heirlooms, every base plant, and all 35 mutants. Undiscovered crossbreeds appear in the **CROSSBREEDS** subsection as **???** silhouettes whose **FIELD NOTES** hint at the parents and condition; discovering one (the id is stored in `profile.json`) permanently reveals its name, stats, exact recipe, and harvest chance, and its seeds join the packs-screen shelf — until then the shelf keeps the secret.

Long weather text, relic descriptions, and heirloom lore are hard-wrapped at glyph boundaries so an unbroken word cannot leak past a panel. HUD lines use measured fitting; toasts wrap to at most two lines; tooltips are anchored near the cursor, flip below it near the top edge, and are clamped to the canvas.

## Controls

| Input | Action |
| --- | --- |
| Left click | Select seeds/plots, water, harvest, shovel, interact with relics, and press buttons |
| Space | Start the round clock; open the next pack on the packs screen; advance dialogue; continue where offered |
| Enter | Continue/confirm on the title, packs, summary, game-over, settings, and confirmation screens |
| X / Delete / Backspace | Toggle the shovel in a round; Backspace also goes back from the Garden Index or Heirloom Shelf |
| Click with the shovel | Dig up a crop (no seed back), clear a weed patch, or cure a diseased plot; weeds need no confirmation |
| Tab | Switch surface/cellar in a round; switch Plants/Upgrades in the Garden Index |
| 1–6 | Select one of the six visible seeds in the round tray |
| 1–8 | Select one of the eight visible seeds to sell on the packs screen |
| Left / Right | Page the seed tray, seed shelf, Garden Index, or heirloom pages |
| A / D | Page the Heirloom Shelf or the owned-heirloom list in the pause panel |
| Up / Down | Cycle Garden Index subsections or page the pack shelves |
| Mouse wheel | Page the hovered packs-screen shelf, round seed tray, Garden Index, or heirloom pages |
| F11 | Toggle fullscreen |
| F12 | Toggle borderless window |
| F2 / F3 | With `BLOOM_DEBUG=1`: toggle 10× round speed / add $10,000 |
| Esc | Cancel shovel or selection mode, close modals and dialogue, go back from index/shelf, or open pause during a run |

## Tutorial

First runs open short, stage-specific walkthroughs with **Moss**. His 96×156 portrait is anchored at the bottom of the 320×180 canvas; the white 216×54 dialogue box covers about a fifth of the screen and advances with a click, Space, Enter, or Right; Left steps back. Arrows highlight the pack button, seed shelf, resale strip, forecast, plots, watering/harvesting, shovel, and shop controls. If the box would cover a target it shifts; if Moss would stand over it, he moves to the other side and the box follows.

Esc or **SKIP** dismisses the tutorial and marks every stage as completed/skipped. Those stage names are stored under `tutorial_done` in `profile.json`, so they do not repeat. The title-screen **GUIDE** button replays a short overview at any time.

`tutorial.py` holds both halves: `DialogueOverlay` is the presentation — pass a list of `DialogueStep`s with optional target rectangles or callables that resolve against the active scene — and the walkthrough steps and story beats are the content fed into it.

## The story, and where it is told

The premise is small on purpose: your Aunt Marigold died owing eight bills, and the will gives you the garden, the shed, and one groundskeeper. You are gardening to pay her debts off, and the eighth payment is the deed.

All of it lives in `tutorial.py` next to the dialogue box that renders it — the opening speech and three lists of beats — so there is one voice and one presentation for Moss:

- `intro_steps()` is the premise, folded onto the **front of the first-run packs walkthrough** rather than a modal of its own. A profile that has already read it gets the two-line version as a round-one beat instead.
- `RUN_BEATS` and `SEASON_BEATS` are the arc (the note in the seed jar, the first bill, the tenants, the last page of the ledger). They play once per run, are remembered in `run.json`, and are keyed to round numbers or to the first round of a season.
- `HAZARD_BEATS` are one warning per twist, played the first time that hazard shows in a forecast. They are remembered in `profile.json` forever: Moss explains a rot once.

Beats are picked up by `App.start_story()`, which the packs screen calls on entry — the one screen a player always looks at before a round and the only one with no clock on it. A beat never stacks on a modal that is already open, and Esc marks it as heard.

Everything else is a hint in text the player is already reading: a `lore` line on each twist is quoted under the forecast, on 25 of the plants in the seed shelf and Garden Index cards, and on the relics and heirlooms that answer a hazard. Lore is flavour only — it never changes a number, and the lore tests in `test_balance.py` hold that line.

## The code and the art

The code is split by responsibility, with `pygame-ce` as the only runtime dependency:

- `app.py` owns the 60 FPS loop, event dispatch, 320×180 canvas, window scaling, toasts, modals, and scene switching.
- `state.py` is the headless simulation: plots, growth, harvesting, weather, relics, bills, serialization. It imports no pygame, only `math`, `random`, and the local `data`/`settings` modules.
- `data.py` holds plants, mutants, packs, relics, heirlooms, twists, seasons, and pairing tables, with each twist, plant, and relic carrying its own `lore` line for the tooltips to quote.
- `settings.py` holds the tuning constants and display geometry.
- `round.py` is the growing screen and calls `Run.update()` each frame; `scene.py` defines the shared `Scene` base class and topbar, and `scenes.py` registers all nine scenes.
- `packs.py`, `shop.py`, `summary.py`, `gameover.py`, `victory.py`, `title.py`, `index.py`, and `overlays.py` cover the other screens and modals.
- `gfx.py` draws the pixel font, panels, buttons, tooltips, sprites, and custom cursor.
- `sprites_data.py` stores every art grid and palette; `ambient.py` draws critters, weather particles, hazard ambience (drifting spores, incoming fireballs, swaying weed), and the cursor snail.

Every plant, relic, and heirloom id in `data.py` must have art in `sprites_data.GRIDS`; `test_balance.py` fails otherwise, which is what keeps the sheet complete as content grows.
- `save.py`, `paths.py`, `formatting.py`, `tutorial.py`, and `preview_sprites.py` handle persistence, save paths, number formatting, Moss's dialogue and beat selection, and sprite inspection.

All sprite art is generated at runtime from character grids in `sprites_data.py`: plant stages, mutant recolours, relic and heirloom badges, seasonal emblems, ambient critters, and the custom 1× cursor with its shadow. Plants are animated by shifting and stretching rows of those grids. There are no external image or audio files, and the system pointer is hidden.

To inspect sprites without starting the game:

```sh
python3 preview_sprites.py daisy sunflower_gold time_capsule --png sheet.png --scale 4
```

With no sprite names it shows every grid. The live window watches `sprites_data.py` and `data.py`, redraws when either file changes, toggles a pixel grid with G, scrolls with the wheel or arrow keys, and closes with Esc. Each sprite is drawn at 2× on soil and 1× on a panel. Regular sprites share one tight grid; art much larger than a 12×12 tile, such as Moss's 96×156 portrait, gets its own labelled rows at the bottom so it does not spread the rest of the sheet apart. Jagged rows, unknown palette keys, and non-12×12 grids are flagged in the preview.

## Tests

From the directory *above* the repository:

```sh
cd ..   # the parent of this directory, so the package name resolves
PYTHONPATH=. SDL_VIDEODRIVER=dummy python3 -m unittest \
    Bloom-Bills.test_balance Bloom-Bills.test_new_mechanics Bloom-Bills.test_tutorial \
    Bloom-Bills.test_crossbreeding
```

The package is this directory itself, so run the tests from its parent: `discover` needs `-s Bloom-Bills -t .`, and importing `Bloom-Bills.test_*` needs the parent on `PYTHONPATH`. From inside the directory the relative imports fail.

That runs **302 tests**: 216 in `test_balance.py` (economy, mechanics, hazards, dialogue, art, and layout), 47 UI/art/index tests, 10 tutorial tests, and 29 crossbreeding tests. They cover bill and price ladders, save/load, weather and boss effects, mutations, packs, seed resale, relic and heirloom effects, plant pairings, sprite coverage and sheet layout, text fitting, the Garden Index, heirloom paging, flytrap critter feeding, the bill-waiver summary UI, crossbreed recipes/adjacency/weather gates/discovery, and rarity ordering of every catalogue. The hazard classes hold the contract that each one is *answerable* — the shovel cures and leaves clean soil, a gap blocks contagion, weeds block soil rather than crops, one watering clears a colony, and every penalty has a relic that answers it. The dialogue classes pin that a beat plays once, on the right screen, in the right save file, and that no story or lore line can change a number. UI tests need `pygame-ce`; `SDL_VIDEODRIVER=dummy` lets them run headless.

## Status

The game is playable start to finish. Paying the eighth bill at round 24 earns the farm, and you can retire with the deed or continue into endless rounds where bills grow 6× every three rounds until one goes unpaid. It is a self-contained prototype with local JSON saves and no external art assets.
