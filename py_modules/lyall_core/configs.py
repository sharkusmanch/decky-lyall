import os

from . import iniconfig
from .errors import OpError

MAX_CONFIG_BYTES = 256 * 1024


def find_config_files(install_path, config_names):
    """Locate catalog-declared config files under the game dir (basename match,
    case-insensitive). Covers ASI .ini next to the DLL and BepInEx/config/*.cfg,
    which only exists after the game's first launch."""
    wanted = {os.path.basename(n).lower() for n in config_names}
    root = os.path.realpath(install_path)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for fname in filenames:
            if fname.lower() in wanted:
                rel = os.path.relpath(os.path.join(dirpath, fname), root)
                found.append({"name": fname, "relpath": rel})
    return sorted(found, key=lambda f: f["relpath"])


def _resolve(install_path, relpath):
    root = os.path.realpath(install_path)
    path = os.path.realpath(os.path.join(root, relpath))
    if os.path.commonpath([root, path]) != root:
        raise OpError("not_found", "config path escapes game dir")
    return path


def _read_text(path):
    try:
        if os.path.getsize(path) > MAX_CONFIG_BYTES:
            raise OpError("unexpected", "config file too large")
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise OpError("not_found", "config file unreadable") from e


def read_entries(install_path, relpath):
    """Parsed entries with a UI type hint per value."""
    text = _read_text(_resolve(install_path, relpath))
    entries = iniconfig.parse(text)
    for e in entries:
        e["type"] = iniconfig.sniff_type(e["value"])
    return entries


def write_value(install_path, relpath, section, key, value):
    path = _resolve(install_path, relpath)
    text = _read_text(path)
    new_text = iniconfig.set_value(text, section, key, str(value))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)
    os.replace(tmp, path)
