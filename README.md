# Bloom & Bills

You have eight bills to pay and a garden to pay them with.

Rounds are 45 seconds long. When the clock hits zero everything in the ground is sold off and the garden is emptied, so each round is planted from scratch with whatever seeds you still have. Every third round the bill collector turns up. The bills go 300, 1,500, 7,500, 37,500 ... and the eighth one is **$23,437,500**. Pay all eight and the farm is yours. Miss one and the run is over, though you keep whatever heirlooms you earned, which make the next run start a little less hopeless.

Every ninth round a new **season** starts - Spring, Summer, Autumn, Winter, then round again. Each season has its own pixel-art emblem in the topbar, and the bar itself is painted to match: mossy green through Spring, sun-baked gold through Summer, rust orange through Autumn and cold blue through Winter, with the same light ink on top all year. The plot lanes stay clean instead of filling with decorative grass; occasional leaves cross the garden in Autumn and sparse snow falls in Winter. Seasons are still cosmetic, while the weather table is what moves your numbers.

It runs in a 320x180 window that scales up cleanly, and it's about ten thousand lines of Python with one dependency.

## A round, start to finish

You open two free seed packs (three seeds each), click a seed, click a plot. Then the actual game starts, which is watering.

A plant grows on its own, slowly. Clicking a growing plot waters it, and a watered plant grows **twice as fast** for four seconds. After that the soil needs three seconds to recover before it'll take water again, so a plot is only running double speed half the time, and only if you keep coming back to it. Four plots at the start, twelve later, all wanting attention, forty-five seconds on the clock.

Click a mature plant to collect its harvest and start its next growth cycle; you can optionally enable automatic harvesting in Settings. A Daisy pays out every five seconds; a Golden Orchid takes twenty-eight and pays 300 when it does. Whatever you've grown by the time the round ends gets sold at the fraction it managed to reach, then it's gone. That's the decision every round: how many seeds to commit to something slow, and whether the money should have gone into a plot instead.

Seeds come from packs, and the good packs cost money, however there's still a chance to get a rarer pack each time.

Unplanted seeds can be sold back. **SELL SEED** under the seed count sells whatever is highlighted in the tray, and its two-row dropdown asks whether to dump one or the whole stack. The price is deliberately low - a quarter of what the grown plant would fetch at the end of a round, so a Daisy seed is $1 and a Golden Orchid seed is $125 - which makes it a way to turn a dead shelf into part of a plot, not a way to farm the shop.

You can highlight any seed you own, including one this board or this weather can't grow, so a frost-banned desert seed can still be turned into cash.

## The bill

Every third round, the collector arrives. The bill is five times the last one. You can refuse to pay; that just ends the run on the spot.

Besides the bill, the things that make rounds go sideways:

- **Weather twists.** Drought slows everything 35%. Locusts cut harvest value 40%. Frost bans desert plants. Rain waters the whole farm for free. Eclipse lets nocturnal plants grow on the surface and makes sun-lovers sulk. Rounds between bills are mostly fair weather, with the odd lucky breeze.
- **Boss rounds**, every ninth. The eight-boss roster rotates through Crazy Crows, Hailstorm, the Autumn-only Garden Ghost, Queen Bee, Root Rot, Heatwave, Eternal Night and Gale. The Ghost swaps two plants and restarts their growth every five seconds; Queen Bee makes every non-flowering surface plant dormant. The crows pick their victim at random, except that a mutated plant is a 20% less appealing meal than a plain one.
- **Mutations.** A plant that keeps surviving harvests starts rolling for a mutation. Ten percent chance, and what comes out is worth two to three times the original. A Golden Sunflower sells for 3x and grows half as fast.
- **Cursed plants.** Devil's Ivy pays well and charges $60 upkeep a round. Widow's Bloom is jealous of its neighbours.
- **The cellar.** $250 to dig out. Four plots, nocturnal plants only, grows without any watering at all, but at three quarters speed. It's the one part of the farm that doesn't need you.

## Relics

Nineteen relics, five slots by default. Relics are what turn a decent round into a silly one: Monoculture pays 2.5x if every plant is the same species, Biodiversity pays for the opposite, a Beehive turns a wall of flowers into a money printer, Scarecrow multiplies every harvest by 1.5, and the Greenhouse doubles all of it.

They get multiply every round - 1.65x, which is deliberately under the 1.71x a round the bills climb, so the shop never prices itself out of the game - and seed packs climb 1.6x alongside them. The interesting question is whether to buy a cheap relic now or save for a scary one later. Some of them also level up mid-run if you hit their counter, which is worth playing around.

## Heirlooms

The permanent stuff, so a failed run still means something. You earn one heirloom per round survived, three per bill paid, and ten for winning. Spend them at the Heirloom Shelf on a few things: end-of-round cash interest (+2% per level up to +25% at max, stacking with Piggy Bank), an extra starting plot, a free pack every round, ten percent to every harvest, and the Relic Cabinet. Prices climb with each level, so the shelf is where a pile of mediocre runs eventually turns into a good one.

## Seeds

Twenty-five base plants across eight packs, plus mutant offshoots that start appearing once a plant has been harvested enough times. The **Farmer Pack** (unlocks round 2) is the field-crop shelf: Potato, Wheat, Corn, Carrot, Cranberries and Saffron, each with its own pixel-art sprite and mutation variant.

The **Desert Pack** is desert-only: Cactus, Aloe Vera, Prickly Pear and Agave. The **Harvest Pack** is autumn-themed: Pumpkin, Corn, Cranberries, Wheat, Potato and Carrot. The **Garden Pack** still stocks Daisy, Tomato and Sunflower, plus Venus Flytrap and Mycelium, and the Golden Orchid is now its one-in-a-hundred jackpot — Cactus swapped out to the Rare Pack. The **Rare Pack** carries Sunflower, Cactus, Pumpkin, Four Leaf Clover and a slim chance at Golden Orchid. Mycelium turns up in both the Garden Pack and the Nocturnal (cellar) pack.

New plants bring new decisions: **Mycelium** creeps into the empty plot to its left, right, up or down, and every connected Mycelium boosts the whole patch's value. Every harvest of the patch has better than a one-in-six chance to push it out one more plot, and on top of that each mycelium fills a creep meter that books a guaranteed spread every 14 seconds of round — you can watch the pale bar under the mushroom fill. A patch only creeps while it has somewhere to go, and one seed stops at six new plots, so a lucky mycelium is a floor under your income, not a free garden; the spread front always grows from the patch's outer edge, so harvesting the original plot never stalls it; **Venus Flytrap** pays little itself but gets fed by every other harvest you take, and its Man-Eater mutation devours an adjacent plant for half its base payout; **Four Leaf Clover** pays nothing but rolls a 25% chance to 1.5x a neighbour's harvest each grow, and it has exactly one mutation, the **Five Leaf Clover**: drawn with five separate leaves, it rolls a 50% chance to 2x instead.

An Eclipse puts the whole nocturnal shelf in the round's tray alongside everything else, which is more than one screenful, so the tray pages with the arrows, left/right or the mouse wheel.

The pack screen is three shelves, and every one of them fits on screen: the unopened packs on the top left (twelve to a page), the seeds and the packs for sale along the bottom. Four packs are for sale at a time and the rest are a page away, so all eight stay reachable through the whole run as each one unlocks - wheel or arrows over a shelf page that shelf. Hovering any pack shows its contents and odds. Farmer, nocturnal and cursed crops can mutate too; cursed mutations retain their upkeep and auras.

## Controls

| Left click | seed, plot, water, harvest, shovel, relic selection, buttons |
| Space | start the round clock |
| X / Backspace / Delete | toggle the shovel to dig up a planted crop |
| Tab | switch between the garden and the cellar |
| 1 - 6 | pick a seed (from the visible tray page) |
| Left / right | page the seed tray / seed shelf / garden index |
| Up / down | change the garden-index subsection / page the pack shelves |
| Mouse wheel | page whichever shelf the cursor is over |
| F11 | fullscreen |
| F12 | borderless window on/off (borderless by default) |
| Esc | open / close pause menu, settings, or confirmation prompts |

## Running it

```
pip install -r requirements.txt
python3 main.py
```

Saves go to `%APPDATA%/BloomAndBills` on Windows, `~/Library/Application Support` on macOS, and `~/.local/share` everywhere else. Set `BLOOM_SAVE_DIR` to point them somewhere else. With `BLOOM_DEBUG=1` you also get F2 to run the round at 10x and F3 to drop $10,000 in your pocket, which is how most of the balance testing got done.

## The code

Small enough to read in an evening:

- `state.py` the whole simulation. It imports nothing but `random`, so you can run rounds headless.
- `data.py` every plant, relic, pack and weather table.
- `settings.py` the knobs worth turning: round length, prices, growth rates.
- `round.py` the growing screen, and the only file with a game loop in it.
- `shop.py`, `packs.py`, `summary.py`, `gameover.py`, `title.py` the other screens.
- `gfx.py` text, panels, buttons, tooltips and the mouse pointer drawn from a pixel font, no image files anywhere.

All the art is generated at runtime from character grids in `sprites_data.py`, which is why the repo is text. That includes the cursor: an outlined, shaded pixel arrow rendered at 2x drawn on the canvas in the same 1px chunks as the font, with the system pointer hidden. Tooltips open with their bottom-left corner on the cursor tip, so the pointer always marks the box it opened.

To look at sprites without starting the game, run `python3 preview_sprites.py daisy my_new_flower` (with no names it shows every sprite). Each one is drawn the way it appears on a plot and in the seed tray, mutant ids like `sunflower_gold` come out in their recolour, and the window redraws whenever `sprites_data.py` is saved, so it can sit open beside the editor. The slips a hand-typed grid invites are spelled out in red: a row that is too long or too short, a letter that is not in `PALETTE`. Add `--png sheet.png` to write a picture instead of opening a window.

## Tests

```
PYTHONPATH=.. python3 -m unittest Bloom-Bills.test_balance
```

Over a hundred tests on the economy, sprites, UI, and mechanics: relic and pack prices climbing (and staying buyable), plot prices tripling, heirloom costs and payouts, the bill ladder, the win condition, seasons and their topbar tints, the Farmer Pack, the Mutagen relic, crow victim weighting, seed resale, sprite coverage across all plants/mutants/relics, and one test per weather twist proving it actually moves a number.

## Where it's at

Version 0.1.0. Playable start to finish, wins at round 24.

## Harvesting and new treasures

Harvesting is manual by default: click a ready plant on either board to collect it; clicking a growing surface plant waters it. Ready plants stay mature until harvested (or sold when the round ends). Enable **Auto Harvest** in Settings to collect immediately, as in the old game. This preference is saved across runs.

The title-screen **Garden Index** is organized under two top sections: **Plants** and **Upgrades**. Plants has category subsections for the garden, desert, farmer crops, night plants, and mutations; Upgrades has **Relics** and **Heirlooms** subsections. Relic pages show price, effects, ownership, and evolution goals, while heirloom pages show permanent levels, current and next bonuses, costs, artwork, and lore.

Ambient critters visit in groups of no more than three. They can walk, hop, or fly completely off screen, stay away briefly, and enter again from another garden edge instead of bouncing against an invisible wall.

**Crystal Bloom** is a slow legendary seed in Rare Packs. Once mature, its next harvest gains $20 base value for every full second left unharvested, before multipliers. The counter resets after harvest; auto-harvesting collects immediately, so it doesn't build this bonus. End-of-round plant sales are separate and don't collect that harvest.

Two rare-to-find **exquisite** relics can appear in the shop. **Clear Skies** rolls once at halfway: on a 25% success the weather or boss ends for the rest of the round, even if it was beneficial. A round's starting duration stays fixed, and effects that already happened aren't undone. **Chosen Bloom** lets you click its name in the relic panel, then click one planted plot on either board each round. That plant grows 50% faster and harvests for twice as much. The choice is spent even if the plant is removed or destroyed.

The three-level **Relic Cabinet** heirloom gives 15% off relics at level 1, a sixth owned relic slot at level 2, and a fourth shop offer at level 3. All benefits carry into future runs.
