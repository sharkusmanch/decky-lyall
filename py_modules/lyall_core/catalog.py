import json
import os
import re
from urllib.parse import urlparse

CATALOG_URL = "https://raw.githubusercontent.com/sharkusmanch/quickfix/master/mods.json"
CACHE_FILE = "catalog.json"

MOD_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
TAG_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Mirrors quickfix's derive_mod_metadata.KNOWN_PROXY_DLLS; dxgi excluded (DXVK conflict).
ALLOWED_OVERRIDES = frozenset({
    "dsound", "winmm", "dinput8", "version", "winhttp",
    "wininet", "d3d9", "d3d10", "d3d11", "d3d12",
    "xinput1_1", "xinput1_2", "xinput1_3", "xinput1_4",
    "xinput9_1_0", "xinputuap", "binkw64", "bink2w64",
})
ALLOWED_LAYOUTS = frozenset({"flat", "pathed"})


def _problems(mod_id, mod):
    p = []
    if not MOD_ID_RE.match(mod_id):
        p.append("bad mod id")
    if mod.get("wine_dll_override") not in ALLOWED_OVERRIDES:
        p.append("missing/unknown wine_dll_override")
    if not SHA256_RE.match(str(mod.get("sha256", ""))):
        p.append("missing/bad sha256")
    url = urlparse(str(mod.get("download_url", "")))
    if url.scheme != "https" or url.hostname != "codeberg.org":
        p.append("bad download_url")
    if not isinstance(mod.get("size"), int) or mod["size"] <= 0:
        p.append("bad size")
    if mod.get("zip_layout") not in ALLOWED_LAYOUTS:
        p.append("bad zip_layout")
    if not TAG_RE.match(str(mod.get("derived_release", ""))):
        p.append("bad derived_release")
    for game in mod.get("games", []):
        if not isinstance(game.get("steam_appid"), int):
            p.append("bad steam_appid")
        subdir = game.get("install_subdir")
        if subdir is not None and (subdir.startswith("/")
                                   or any(seg == ".." for seg in subdir.split("/"))):
            p.append(f"unsafe install_subdir: {subdir!r}")
    return p


def usable_mods(raw):
    """Split a raw catalog into (usable, skipped) — defense in depth on remote input."""
    usable, skipped = {}, {}
    for mod_id, mod in raw.items():
        problems = _problems(mod_id, mod)
        if problems:
            skipped[mod_id] = problems
        else:
            usable[mod_id] = mod
    return usable, skipped


def _cache_path(settings_dir):
    return os.path.join(settings_dir, CACHE_FILE)


def save_cache(settings_dir, raw, fetched_at):
    os.makedirs(settings_dir, exist_ok=True)
    with open(_cache_path(settings_dir), "w", encoding="utf-8") as f:
        json.dump({"fetched_at": fetched_at, "mods": raw}, f)


def load_cache(settings_dir):
    try:
        with open(_cache_path(settings_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data["mods"], data.get("fetched_at")
    except (OSError, ValueError, KeyError):
        return None, None
