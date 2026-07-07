import os

# exe-name substrings that are never a game's main executable
_STUB_EXE = (
    "crashpad", "crashhandler", "crashreport", "unitycrashhandler",
    "launcher", "startup", "unins", "vcredist", "dxsetup", "dxwebsetup",
    "easyanticheat", "battleye", "redist", "dotnet", "oalinst",
    "benchmark", "setup", "activation", "touchup", "cleanup", "helper",
)

# directory suffixes that strongly indicate the shipping-exe folder
_ENGINE_DIRS = ("binaries/win64", "binaries/wingdk", "runtime/media")

_ENGINE_BONUS = 1 << 40  # dominates raw file size so engine dirs rank first


def _is_stub(name):
    low = name.lower()
    return any(s in low for s in _STUB_EXE)


def detect_install_subdir(install_path, limit=5):
    """Rank candidate extraction directories (relative to install_path) by where
    the game's shipping exe most likely lives. This PROPOSES; the user confirms —
    it never installs on its own. Returns [{subdir, exe}] best-first."""
    best = {}  # subdir -> (score, exe_relpath)
    root = os.path.realpath(install_path)
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(dp, d))]
        for f in files:
            if not f.lower().endswith(".exe") or _is_stub(f):
                continue
            try:
                size = os.path.getsize(os.path.join(dp, f))
            except OSError:
                continue
            rel = os.path.relpath(os.path.join(dp, f), root)
            subdir = os.path.dirname(rel) or "."
            score = size
            if any(subdir.lower().endswith(e) for e in _ENGINE_DIRS):
                score += _ENGINE_BONUS
            if subdir not in best or score > best[subdir][0]:
                best[subdir] = (score, rel)
    ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
    return [{"subdir": sd, "exe": exe} for sd, (_, exe) in ranked[:limit]]
