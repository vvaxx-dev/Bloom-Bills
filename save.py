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
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
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
            profile = self._read_json(self.profile_path)
            if profile is None:
                backup = self.profile_path.with_name(self.profile_path.name + ".bak")
                self.profile_path.replace(backup)
        if profile is None:
            profile = {k: v.copy() if isinstance(v, (dict, list)) else v for k, v in PROFILE_DEFAULT.items()}
        for key, value in PROFILE_DEFAULT.items():
            profile.setdefault(key, value.copy() if isinstance(value, (dict, list)) else value)

        for key in ("v", "heirlooms", "best_round", "runs", "wins"):
            val = profile.get(key)
            if isinstance(val, bool):
                profile[key] = PROFILE_DEFAULT[key]
            else:
                try:
                    profile[key] = int(val)
                except (TypeError, ValueError):
                    profile[key] = PROFILE_DEFAULT[key]

        raw_perks = profile.get("perks")
        clean_perks = {}
        if isinstance(raw_perks, dict):
            for key, value in raw_perks.items():
                if not isinstance(value, bool):
                    try:
                        clean_perks[str(key)] = int(value)
                    except (TypeError, ValueError):
                        pass
        profile["perks"] = clean_perks

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
            {str(k): int(v) for k, v in raw_harvested.items()
             if isinstance(v, (int, float)) and not isinstance(v, bool)}
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
        if "story_seen" in profile:
            raw_story = profile.get("story_seen")
            profile["story_seen"] = (
                [str(x) for x in raw_story if isinstance(x, str)]
                if isinstance(raw_story, list) else []
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
