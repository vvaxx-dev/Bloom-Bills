"""Persistent profile and mid-run save management using atomic temp-file writes."""

import json

from .paths import save_dir

SETTINGS_DEFAULT = {"confirmations": True, "floaters": True, "auto_harvest": False, "scale": 6}
PROFILE_DEFAULT = {
    "v": 1, "heirlooms": 0, "perks": {}, "best_round": 0, "runs": 0, "wins": 0,
    "settings": SETTINGS_DEFAULT.copy(), "harvested": {}, "tutorial_done": [],
    "discovered_crossbreeds": [],
}


def _atomic_write(path, payload):
    """Write JSON to a sibling .tmp file and replace atomically to prevent partial saves."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


class SaveManager:
    """Reads and writes persistent profile progress and active-run snapshots."""

    def __init__(self):
        self.folder = save_dir()
        self.profile_path = self.folder / "profile.json"
        self.run_path = self.folder / "run.json"

    def _read_json(self, path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def load_profile(self):
        """Load profile.json, filling missing keys and clamping settings to valid bounds.

        A corrupt profile.json is moved to profile.json.bak instead of being
        silently replaced with defaults: the defaults only live in memory
        until the next save, so the player's heirlooms and crossbreed index
        are not wiped out from under them.
        """
        profile = None
        if self.profile_path.exists():
            try:
                profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                profile = None
            if not isinstance(profile, dict):
                backup = self.profile_path.with_name(self.profile_path.name + ".bak")
                self.profile_path.replace(backup)
                profile = None
        if profile is None:
            profile = PROFILE_DEFAULT.copy()
        for key, value in PROFILE_DEFAULT.items():
            profile.setdefault(key, value.copy() if isinstance(value, dict) else value)
        profile["perks"] = {key: int(value) for key, value in profile["perks"].items()}

        raw_settings = profile.get("settings")
        merged_settings = dict(SETTINGS_DEFAULT)
        if isinstance(raw_settings, dict):
            merged_settings["confirmations"] = bool(raw_settings.get("confirmations", True))
            merged_settings["floaters"] = bool(raw_settings.get("floaters", True))
            merged_settings["auto_harvest"] = bool(raw_settings.get("auto_harvest", False))
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
        raw_crossbreeds = profile.get("discovered_crossbreeds")
        profile["discovered_crossbreeds"] = (
            sorted({str(x) for x in raw_crossbreeds if isinstance(x, str)})
            if isinstance(raw_crossbreeds, list) else []
        )
        raw_tutorial = profile.get("tutorial_done")
        profile["tutorial_done"] = (
            [str(x) for x in raw_tutorial if isinstance(x, str)]
            if isinstance(raw_tutorial, list) else []
        )
        return profile

    def save_profile(self, profile):
        _atomic_write(self.profile_path, profile)

    def load_run(self):
        """Load the active run snapshot; a corrupt run.json is moved to run.json.bak."""
        if not self.run_path.exists():
            return None
        data = self._read_json(self.run_path)
        if data is None:
            backup = self.run_path.with_name(self.run_path.name + ".bak")
            self.run_path.replace(backup)
        return data

    def save_run(self, run):
        _atomic_write(self.run_path, run)

    def clear_run(self):
        try:
            self.run_path.unlink()
        except FileNotFoundError:
            pass
