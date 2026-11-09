import json

from .paths import save_dir

SETTINGS_DEFAULT = {"confirmations": True, "floaters": True, "scale": 6}
PROFILE_DEFAULT = {
    "v": 1, "heirlooms": 0, "perks": {}, "best_round": 0, "runs": 0, "wins": 0,
    "settings": SETTINGS_DEFAULT.copy(), "harvested": {},
}


class SaveManager:
    def __init__(self):
        self.folder = save_dir()
        self.profile_path = self.folder / "profile.json"
        self.run_path = self.folder / "run.json"

    def _load(self, path, default):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else default.copy()
        except (OSError, json.JSONDecodeError):
            return default.copy()

    def load_profile(self):
        profile = self._load(self.profile_path, PROFILE_DEFAULT)
        for key, value in PROFILE_DEFAULT.items():
            profile.setdefault(key, value.copy() if isinstance(value, dict) else value)
        profile["perks"] = {key: int(value) for key, value in profile["perks"].items()}
        raw_settings = profile.get("settings")
        merged_settings = dict(SETTINGS_DEFAULT)
        if isinstance(raw_settings, dict):
            merged_settings["confirmations"] = bool(raw_settings.get("confirmations", True))
            merged_settings["floaters"] = bool(raw_settings.get("floaters", True))
            try:
                merged_settings["scale"] = max(2, min(8, int(raw_settings.get("scale", 6))))
            except (TypeError, ValueError):
                merged_settings["scale"] = 6
        profile["settings"] = merged_settings
        raw_harvested = profile.get("harvested")
        profile["harvested"] = (
            {str(k): int(v) for k, v in raw_harvested.items() if isinstance(v, (int, float))}
            if isinstance(raw_harvested, dict) else {}
        )
        return profile

    def save_profile(self, profile):
        self.profile_path.with_suffix(".json.tmp").write_text(json.dumps(profile), encoding="utf-8")
        self.profile_path.with_suffix(".json.tmp").replace(self.profile_path)

    def load_run(self):
        try:
            data = json.loads(self.run_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def save_run(self, run):
        self.run_path.with_suffix(".json.tmp").write_text(json.dumps(run), encoding="utf-8")
        self.run_path.with_suffix(".json.tmp").replace(self.run_path)

    def clear_run(self):
        try:
            self.run_path.unlink()
        except FileNotFoundError:
            pass
