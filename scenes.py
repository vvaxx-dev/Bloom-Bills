
from .gameover import GameOverScene, ShelfScene
from .packs import PacksScene
from .round import RoundScene
from .shop import ShopScene
from .summary import SummaryScene
from .title import TitleScene

SCENES = {
    "title": TitleScene,
    "packs": PacksScene,
    "round": RoundScene,
    "summary": SummaryScene,
    "shop": ShopScene,
    "gameover": GameOverScene,
    "shelf": ShelfScene,
}
