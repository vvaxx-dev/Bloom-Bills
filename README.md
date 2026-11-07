# Bloom & Bills

You have eight bills to pay and a garden to pay them with.

Rounds are 45 seconds long. When the clock hits zero everything in the ground is sold off and the garden is emptied, so each round is planted from scratch with whatever seeds you still have. Every third round the bill collector turns up. The bills go 300, 1,500, 7,500, 37,500 ... and the eighth one is **$23,437,500**. Pay all eight and the farm is yours. Miss one and the run is over, though you keep whatever heirlooms you earned, which make the next run start a little less hopeless.

It runs in a 320x180 window that scales up cleanly, and it's about three thousand lines of Python with one dependency.

## A round, start to finish

You open two free seed packs (three seeds each), click a seed, click a plot. Then the actual game starts, which is watering.

A plant grows on its own, slowly. Clicking a growing plot waters it, and a watered plant grows **twice as fast** for three seconds. After that the soil needs three seconds to recover before it'll take water again, so a plot is only running double speed half the time, and only if you keep coming back to it. Four plots at the start, twelve later, all wanting attention, forty-five seconds on the clock.

Harvests fire on their own the moment a plant finishes, pay out immediately, and the plant starts over. A Daisy pays out every five seconds; a Golden Orchid takes twenty-eight and pays 300 when it does. Whatever you've grown by the time the round ends gets sold at the fraction it managed to reach, then it's gone. That's the decision every round: how much seed to commit to something slow, and whether the money should have gone into a plot instead.

Seeds come from packs, and the good packs cost money, which is the loop closing on itself.

## The bill

Every third round, the collector arrives. The bill is five times the last one. You can refuse to pay; that just ends the run on the spot.

Besides the bill, the things that make rounds go sideways:

- **Weather twists.** Drought slows everything 35%. Locusts cut harvest value 40%. Frost bans desert plants. Rain waters the whole farm for free. Eclipse lets nocturnal plants grow on the surface and makes sun-lovers sulk. Rounds between bills are mostly fair weather, with the odd lucky breeze.
- **Boss rounds**, every ninth. Crow Swarm: a crow eats a random plant every ten seconds, and it does not care which one you were saving.
- **Mutations.** A plant that keeps surviving harvests starts rolling for a mutation. Ten percent chance, and what comes out is worth two to three times the original. A Golden Sunflower sells for 3x and grows half as fast.
- **Cursed plants.** Devil's Ivy pays well and charges $60 upkeep a round. Widow's Bloom is jealous of its neighbours.
- **The cellar.** $250 to dig out. Four plots, nocturnal plants only, grows without any watering at all, but at three quarters speed. It's the one part of the farm that doesn't need you.

## Relics

Sixteen relics, five slots. Relics are what turn a decent round into a silly one: Monoculture pays 2.5x if every plant is the same species, Biodiversity pays for the opposite, a Beehive turns a wall of flowers into a money printer, Scarecrow multiplies every harvest by 1.5, and the Greenhouse doubles all of it.

They get dearer every round, fast, so the interesting question is whether to buy a cheap relic now or save for a scary one later. Some of them also level up mid-run if you hit their counter, which is worth playing around.

## Heirlooms

The permanent stuff, so a failed run still means something. You earn one heirloom per round survived, three per bill paid, and ten for winning. Spend them at the Heirloom Shelf on four things: starting cash, an extra starting plot, a free pack every round, and ten percent to every harvest. Prices climb with each level, so the shelf is where a pile of mediocre runs eventually turns into a good one.

## Controls

| Key | Does |
|---|---|
| Left click | everything. Seed, plot, water, buttons |
| Space | start the round clock |
| Tab | switch between the garden and the cellar |
| 1 - 6 | pick a seed |
| F11 | fullscreen |
| Esc | back to the title |

## Running it

```
pip install -r requirements.txt
python3 main.py
```

Saves go to `%APPDATA%/BloomAndBills` on Windows, `~/Library/Application Support` on macOS, and `~/.local/share` everywhere else. Set `BLOOM_SAVE_DIR` to point them somewhere else. With `BLOOM_DEBUG=1` you also get F2 to run the round at 10x and F3 to drop $10,000 in your pocket, which is how most of the balance testing got done.

## The code

Small enough to read in an evening:

- `state.py` the whole simulation. It imports nothing but `random`, so you can run rounds headless.
- `data.py` every plant, relic, pack and weather table. Balance lives here.
- `settings.py` the knobs worth turning: round length, prices, growth rates.
- `round.py` the growing screen, and the only file with a game loop in it.
- `shop.py`, `packs.py`, `summary.py`, `gameover.py`, `title.py` the other screens.
- `gfx.py` text, panels, buttons drawn from a pixel font, no image files anywhere.

All the art is generated at runtime from character grids in `sprites_data.py`, which is why the repo is text.

## Tests

```
python3 -m unittest Plant_Game.test_balance
```

Twenty-nine tests on the economy: relic prices climbing, plot prices tripling, heirloom costs and payouts, the bill ladder, and the win condition.

## Where it's at

Version 0.1.0. Playable start to finish, wins at round 24.
