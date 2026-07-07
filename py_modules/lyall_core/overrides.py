import copy
import json
import os

OVERRIDES_FILE = "curation_overrides.json"


def safe_subdir(subdir):
    """A subdir override must be relative with no parent traversal ('.' = root)."""
    if not isinstance(subdir, str) or subdir.startswith("/"):
        return False
    return not any(seg == ".." for seg in subdir.split("/"))


def _path(settings_dir):
    return os.path.join(settings_dir, OVERRIDES_FILE)


def load(settings_dir):
    """{str(appid): {mod_id: subdir}} — user-confirmed install paths, local only."""
    try:
        with open(_path(settings_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def set_subdir(settings_dir, appid, mod_id, subdir):
    ov = load(settings_dir)
    ov.setdefault(str(appid), {})[mod_id] = subdir
    os.makedirs(settings_dir, exist_ok=True)
    with open(_path(settings_dir), "w", encoding="utf-8") as f:
        json.dump(ov, f, indent=2)
    return ov


def apply(mods, ov):
    """Layer overrides onto a catalog copy: fill games[].install_subdir from ov.
    Unsafe subdirs are ignored. Never mutates the input."""
    out = copy.deepcopy(mods)
    for mod_id, mod in out.items():
        for game in mod.get("games", []):
            sub = ov.get(str(game.get("steam_appid")), {}).get(mod_id)
            if sub and safe_subdir(sub):
                game["install_subdir"] = sub
    return out
