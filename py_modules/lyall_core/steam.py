import os
import re

_ROOT_CANDIDATES = (".local/share/Steam", ".steam/steam", ".steam/root")
_SKIP_NAMES = ("Proton", "Steam Linux Runtime", "Steamworks Common")

_PATH_RE = re.compile(r'"path"\s+"([^"]+)"')
_KV_RE = {
    "appid": re.compile(r'"appid"\s+"(\d+)"'),
    "name": re.compile(r'"name"\s+"([^"]*)"'),
    "installdir": re.compile(r'"installdir"\s+"([^"]+)"'),
}


def find_steam_root(home):
    for cand in _ROOT_CANDIDATES:
        path = os.path.join(home, cand)
        if os.path.isdir(os.path.join(path, "steamapps")):
            return os.path.realpath(path)
    return None


def library_paths(steam_root):
    """All steamapps dirs: parsed from libraryfolders.vdf, plus the root itself."""
    paths = []
    vdf = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = _PATH_RE.search(line)
                if m:
                    paths.append(os.path.join(m.group(1), "steamapps"))
    except OSError:
        pass
    root_steamapps = os.path.join(steam_root, "steamapps")
    if root_steamapps not in paths:
        paths.append(root_steamapps)
    return [p for p in paths if os.path.isdir(p)]


def parse_appmanifest(text):
    out = {}
    for key, rx in _KV_RE.items():
        m = rx.search(text)
        if not m:
            return None
        out[key] = m.group(1)
    return {"appid": int(out["appid"]), "name": out["name"], "installdir": out["installdir"]}


def installed_games(steam_root):
    """{appid: {name, install_path}} for games whose install dir exists on disk."""
    games = {}
    for lib in library_paths(steam_root):
        for entry in os.listdir(lib):
            if not (entry.startswith("appmanifest_") and entry.endswith(".acf")):
                continue
            try:
                with open(os.path.join(lib, entry), encoding="utf-8", errors="replace") as f:
                    parsed = parse_appmanifest(f.read())
            except OSError:
                continue
            if not parsed or any(s in parsed["name"] for s in _SKIP_NAMES):
                continue
            install_path = os.path.join(lib, "common", parsed["installdir"])
            if os.path.isdir(install_path) and parsed["appid"] not in games:
                games[parsed["appid"]] = {"name": parsed["name"], "install_path": install_path}
    return games
