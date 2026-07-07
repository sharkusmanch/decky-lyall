# decky-lyall Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Decky Loader plugin ("Lyall Fixes") that installs/updates/uninstalls Lyall's game fixes into Steam game dirs on SteamOS and registers `WINEDLLOVERRIDES` toggles with the Launch Options (DLO) plugin.

**Architecture:** Python backend (`main.py` thin glue over unit-tested pure modules in `py_modules/lyall_core/`) does catalog fetch/validation, Steam library scanning, pinned+hash-verified downloads, hardened extraction with pristine backups and manifests. React frontend (QAM panel) renders per-game rows, drives installs, and handles all launch-option UX (DLO event dispatch or manual copy fallback). Frontend↔backend via `@decky/api` callables + `qf_progress`/`qf_done` events.

**Tech Stack:** Python 3.11 (Decky's frozen runtime: aiohttp + certifi available, no pip), pytest + pytest-asyncio; TypeScript/React with `@decky/ui` 4.x, `@decky/api` 1.x, rollup via `@decky/rollup`, pnpm 9, vitest. Repo: `/config/decky-lyall` (empty). Distribution: GitHub release zip + Decky "Install from URL".

**Spec:** `/config/quickfix/docs/superpowers/specs/2026-07-06-decky-quickfix-plugin-design.md` (Part 2). Research: `/config/games/quickfix-decky-plugin/research/`.

**Depends on:** Catalog v2 plan (quickfix repo) merged — the plugin consumes `wine_dll_override`/`sha256`/`download_url`/`zip_layout`/`install_subdir`/`derived_release`. Backend modules can be built and tested before that merges (tests use synthetic catalogs).

**Note on backend testability:** the `decky` module only exists inside Decky Loader. All logic lives in `py_modules/lyall_core/` (imports nothing Decky-specific; paths and emit functions are injected). `main.py` is untested glue.

---

### Task 0: Toolchain + repo init

- [ ] **Step 1: Install toolchain in the pod**

```bash
~/.local/bin/mise use -g node@20
npm install -g pnpm@9
pip install --user pytest pytest-asyncio
```

Run: `node --version && pnpm --version && python3 -m pytest --version`
Expected: node v20.x, pnpm 9.x, pytest present.

- [ ] **Step 2: Init repo on main**

```bash
cd /config/decky-lyall && git switch -c main 2>/dev/null || git checkout -b main
```

- [ ] **Step 3: Commit this plan** (it lives in this repo)

```bash
git add docs/ && git commit -m "docs: implementation plan"
```

---

### Task 1: Scaffold plugin skeleton

**Files:**
- Create: `plugin.json`, `package.json`, `tsconfig.json`, `rollup.config.js`, `.gitignore`, `LICENSE`, `pytest.ini`, `conftest.py`, `decky.pyi`, `py_modules/lyall_core/__init__.py` (empty), `tests/__init__.py` (empty), `src/index.tsx` (stub)

- [ ] **Step 1: Write config files**

`plugin.json`:

```json
{
  "name": "Lyall Fixes",
  "author": "sharkusmanch",
  "flags": [],
  "api_version": 1,
  "publish": {
    "tags": ["mods", "game-fixes"],
    "description": "Install Lyall's PC game fixes from Gaming Mode",
    "image": "https://opengraph.githubassets.com/1/sharkusmanch/decky-lyall"
  }
}
```

`package.json`:

```json
{
  "name": "decky-lyall",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "build": "rollup -c",
    "watch": "rollup -c -w",
    "test": "vitest run"
  },
  "dependencies": {
    "@decky/api": "^1.1.3",
    "react-icons": "^5.3.0"
  },
  "devDependencies": {
    "@decky/rollup": "^1.0.2",
    "@decky/ui": "^4.11.6",
    "@types/react": "19.1.1",
    "rollup": "^4.22.0",
    "typescript": "^5.6.0",
    "vitest": "^3.0.0"
  },
  "packageManager": "pnpm@9.15.0"
}
```

`rollup.config.js`:

```javascript
import deckyPlugin from "@decky/rollup";

export default deckyPlugin({});
```

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "outDir": "dist",
    "module": "ESNext",
    "target": "ES2020",
    "jsx": "react",
    "jsxFactory": "window.SP_REACT.createElement",
    "jsxFragmentFactory": "window.SP_REACT.Fragment",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

`.gitignore`:

```
node_modules/
dist/
out/
__pycache__/
.pytest_cache/
*.log
```

`pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

`conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "py_modules"))
```

`LICENSE`: MIT, copyright 2026 sharkusmanch (copy the text from `/config/quickfix/LICENSE`, update year/name if needed).

`src/index.tsx` (stub, replaced in Task 10):

```tsx
import { definePlugin } from "@decky/api";
import { staticClasses } from "@decky/ui";

export default definePlugin(() => ({
  name: "Lyall Fixes",
  titleView: <div className={staticClasses.Title}>Lyall Fixes</div>,
  content: <div>Loading…</div>,
  icon: <span>🔧</span>,
}));
```

- [ ] **Step 2: Fetch decky type stubs from the official template**

```bash
curl -fsSL -o decky.pyi https://raw.githubusercontent.com/SteamDeckHomebrew/decky-plugin-template/main/decky.pyi
```

- [ ] **Step 3: Install and build**

Run: `pnpm install && pnpm run build`
Expected: `dist/index.js` produced without errors. If `jsxFactory` settings conflict with `@decky/rollup` defaults, defer to the template's current `tsconfig.json` (`curl -fsSL https://raw.githubusercontent.com/SteamDeckHomebrew/decky-plugin-template/main/tsconfig.json`) — the build passing is the acceptance test.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: plugin skeleton (template-equivalent scaffold)"
```

---

### Task 2: `errors.py` — typed errors + result envelopes

**Files:**
- Create: `py_modules/lyall_core/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

`tests/test_errors.py`:

```python
from lyall_core.errors import OpError, fail, ok


def test_fail_uses_default_message():
    env = fail("game_running")
    assert env == {"ok": False, "code": "game_running",
                   "message": "Close the game before installing"}


def test_fail_unknown_code_falls_back():
    env = fail("bogus")
    assert env["ok"] is False and env["message"]


def test_ok_merges_fields():
    assert ok(accepted=True) == {"ok": True, "accepted": True}


def test_operror_carries_code_and_message():
    e = OpError("verify_failed")
    assert e.code == "verify_failed" and "verification" in e.message
```

- [ ] **Step 2: Run to verify failure** — `python3 -m pytest tests/test_errors.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement**

`py_modules/lyall_core/errors.py`:

```python
MESSAGES = {
    "network_offline": "No connection — using cached data",
    "verify_failed": "Download failed verification — try Refresh",
    "no_asset": "No downloadable release for this fix",
    "extract_failed": "Install failed — game files restored",
    "game_running": "Close the game before installing",
    "already_in_progress": "Another operation is running for this game",
    "needs_curation": "Awaiting catalog data for this game",
    "not_found": "Unknown mod or game",
    "unexpected": "Something went wrong — check the Decky log",
}


class OpError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or MESSAGES.get(code, MESSAGES["unexpected"])
        super().__init__(self.message)


def fail(code, message=None):
    return {"ok": False, "code": code,
            "message": message or MESSAGES.get(code, MESSAGES["unexpected"])}


def ok(**fields):
    return {"ok": True, **fields}
```

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_errors.py -v` → 4 PASS.

- [ ] **Step 5: Commit** — `git add py_modules tests && git commit -m "feat: error codes and result envelopes"`

---

### Task 3: `catalog.py` — validation, fetch, cache

**Files:**
- Create: `py_modules/lyall_core/catalog.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_catalog.py`:

```python
import json

from lyall_core import catalog


def _mod(**over):
    m = {
        "repo": "Lyall/FooFix",
        "config_files": ["FooFix.ini"],
        "games": [{"steam_appid": 42, "install_subdir": "Foo/Binaries/Win64"}],
        "wine_dll_override": "dsound",
        "loader": "ual",
        "zip_layout": "flat",
        "derived_release": "0.0.1",
        "download_url": "https://codeberg.org/Lyall/FooFix/releases/download/0.0.1/F.zip",
        "sha256": "0" * 64,
        "size": 100,
    }
    m.update(over)
    return m


def test_valid_mod_is_usable():
    usable, skipped = catalog.usable_mods({"FooFix": _mod()})
    assert "FooFix" in usable and not skipped


def test_rejects_bad_mod_id():
    usable, skipped = catalog.usable_mods({"../evil": _mod()})
    assert not usable and "../evil" in skipped


def test_rejects_missing_override_or_pinning():
    for missing in ("wine_dll_override", "sha256", "download_url", "size"):
        mod = _mod()
        del mod[missing]
        usable, _ = catalog.usable_mods({"FooFix": mod})
        assert not usable, missing


def test_rejects_unknown_override_and_offsite_url():
    assert not catalog.usable_mods({"F": _mod(wine_dll_override="dxgi")})[0]
    assert not catalog.usable_mods({"F": _mod(download_url="https://evil.com/x.zip")})[0]


def test_rejects_traversal_subdir_and_bad_appid():
    bad = _mod()
    bad["games"] = [{"steam_appid": 42, "install_subdir": "a/../../b"}]
    assert not catalog.usable_mods({"F": bad})[0]
    bad2 = _mod()
    bad2["games"] = [{"steam_appid": "42"}]
    assert not catalog.usable_mods({"F": bad2})[0]


def test_cache_roundtrip(tmp_path):
    raw = {"FooFix": _mod()}
    catalog.save_cache(str(tmp_path), raw, fetched_at="2026-07-06T00:00:00+00:00")
    loaded, fetched_at = catalog.load_cache(str(tmp_path))
    assert loaded == raw and fetched_at == "2026-07-06T00:00:00+00:00"


def test_load_cache_missing_returns_none(tmp_path):
    assert catalog.load_cache(str(tmp_path)) == (None, None)
```

- [ ] **Step 2: Run to verify failure** — `python3 -m pytest tests/test_catalog.py -v` → FAIL.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/catalog.py`:

```python
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
```

(The aiohttp fetch lives in `main.py` — it needs Decky's certifi context and is glue, not logic: GET `CATALOG_URL`, `json.loads`, `save_cache`.)

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_catalog.py -v` → all PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: catalog validation and cache"`

---

### Task 4: `steam.py` — root discovery, library + appmanifest parsing

**Files:**
- Create: `py_modules/lyall_core/steam.py`
- Test: `tests/test_steam.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_steam.py`:

```python
import os

from lyall_core import steam

LIBRARYFOLDERS = '''"libraryfolders"
{
\t"0"
\t{
\t\t"path"\t\t"{root}"
\t}
\t"1"
\t{
\t\t"path"\t\t"{sd}"
\t}
}
'''

APPMANIFEST = '''"AppState"
{
\t"appid"\t\t"1903340"
\t"name"\t\t"Clair Obscur: Expedition 33"
\t"installdir"\t\t"Expedition 33"
}
'''


def _mk_steam(tmp_path):
    root = tmp_path / ".local/share/Steam"
    sd = tmp_path / "sdcard"
    for lib in (root, sd):
        (lib / "steamapps/common").mkdir(parents=True)
    (root / "steamapps/libraryfolders.vdf").write_text(
        LIBRARYFOLDERS.replace("{root}", str(root)).replace("{sd}", str(sd)))
    (sd / "steamapps/appmanifest_1903340.acf").write_text(APPMANIFEST)
    (sd / "steamapps/common/Expedition 33").mkdir()
    return root, sd


def test_find_steam_root(tmp_path):
    root, _ = _mk_steam(tmp_path)
    assert steam.find_steam_root(str(tmp_path)) == str(root)


def test_find_steam_root_missing(tmp_path):
    assert steam.find_steam_root(str(tmp_path)) is None


def test_library_paths_include_root_and_sd(tmp_path):
    root, sd = _mk_steam(tmp_path)
    libs = steam.library_paths(str(root))
    assert str(root / "steamapps") in libs and str(sd / "steamapps") in libs


def test_installed_games(tmp_path):
    root, sd = _mk_steam(tmp_path)
    games = steam.installed_games(str(root))
    assert games[1903340]["install_path"] == str(sd / "steamapps/common/Expedition 33")
    assert games[1903340]["name"] == "Clair Obscur: Expedition 33"


def test_skips_runtime_entries(tmp_path):
    root, sd = _mk_steam(tmp_path)
    (sd / "steamapps/appmanifest_1628350.acf").write_text(
        APPMANIFEST.replace("1903340", "1628350")
        .replace("Clair Obscur: Expedition 33", "Steam Linux Runtime 3.0 (sniper)")
        .replace("Expedition 33", "SteamLinuxRuntime_sniper"))
    assert 1628350 not in steam.installed_games(str(root))
```

- [ ] **Step 2: Run to verify failure** — FAIL, module missing.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/steam.py`:

```python
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
```

- [ ] **Step 4: Run** — all PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: steam library scanning"`

---

### Task 5: `extract.py` — hardened extractor

**Files:**
- Create: `py_modules/lyall_core/extract.py`
- Test: `tests/test_extract.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_extract.py`:

```python
import io
import os
import zipfile

import pytest

from lyall_core import extract
from lyall_core.errors import OpError


def _zf(entries):
    """entries: {name: bytes} or a list of (ZipInfo, bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if isinstance(entries, dict):
            for name, data in entries.items():
                z.writestr(name, data)
        else:
            for info, data in entries:
                z.writestr(info, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def _run(zf, target, staging, owned=frozenset(), backups=None):
    return extract.safe_extract(zf, str(target), str(staging),
                                owned_files=owned, backup_dir=str(backups or target / ".bk"))


def test_basic_extraction(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    written, backed = _run(_zf({"Fix.asi": b"a", "dsound.dll": b"d"}), t, s)
    assert (t / "Fix.asi").read_bytes() == b"a"
    assert sorted(written) == ["Fix.asi", "dsound.dll"] and backed == []


def test_backslash_entries_become_dirs(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    _run(_zf({"End\\Binaries\\Win64\\dsound.dll": b"d"}), t, s)
    assert (t / "End/Binaries/Win64/dsound.dll").exists()


def test_marker_file_skipped(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    written, _ = _run(_zf({"EXTRACT_TO_GAME_FOLDER": b"", "Fix.asi": b"a"}), t, s)
    assert written == ["Fix.asi"]


@pytest.mark.parametrize("name", ["../evil.dll", "a/../../evil.dll", "/etc/evil", "C:/evil.dll"])
def test_unsafe_paths_rejected(tmp_path, name):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    with pytest.raises(OpError):
        _run(_zf({name: b"x"}), t, s)
    assert not (tmp_path / "evil.dll").exists()


def test_symlink_entries_skipped(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    info = zipfile.ZipInfo("link")
    info.external_attr = 0o120777 << 16  # S_IFLNK
    written, _ = _run(_zf([(info, b"/etc/passwd"), (zipfile.ZipInfo("Fix.asi"), b"a")]), t, s)
    assert written == ["Fix.asi"] and not (t / "link").exists()


def test_case_insensitive_merge(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    (t / "End/Binaries/Win64").mkdir(parents=True); s.mkdir()
    _run(_zf({"end/binaries/win64/dsound.dll": b"d"}), t, s)
    assert (t / "End/Binaries/Win64/dsound.dll").exists()
    assert not (t / "end").exists()


def test_pristine_backup_only_for_unowned_files(tmp_path):
    t, s, bk = tmp_path / "game", tmp_path / "staging", tmp_path / "bk"
    t.mkdir(); s.mkdir()
    (t / "game.ini").write_bytes(b"original")   # pristine game file
    (t / "Fix.asi").write_bytes(b"old-mod")     # our own previous version
    written, backed = _run(_zf({"game.ini": b"modded", "Fix.asi": b"new-mod"}), t, s,
                           owned={"Fix.asi"}, backups=bk)
    assert backed == ["game.ini"]
    assert (bk / "game.ini").read_bytes() == b"original"
    assert not (bk / "Fix.asi").exists()


def test_backups_are_write_once(tmp_path):
    t, s, bk = tmp_path / "game", tmp_path / "staging", tmp_path / "bk"
    t.mkdir(); s.mkdir(); bk.mkdir()
    (bk / "game.ini").write_bytes(b"original")
    (t / "game.ini").write_bytes(b"already-modded")
    _run(_zf({"game.ini": b"modded-again"}), t, s, backups=bk)
    assert (bk / "game.ini").read_bytes() == b"original"


def test_rollback_on_failure(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    (t / "exists.txt").write_bytes(b"original")
    zf = _zf({"exists.txt": b"overwritten", "ok.txt": b"new", "../evil": b"x"})
    with pytest.raises(OpError):
        _run(zf, t, s)
    assert (t / "exists.txt").read_bytes() == b"original"
    assert not (t / "ok.txt").exists()


def test_entry_count_cap(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    extract.MAX_ENTRIES, saved = 3, extract.MAX_ENTRIES
    try:
        with pytest.raises(OpError):
            _run(_zf({f"f{i}": b"x" for i in range(4)}), t, s)
    finally:
        extract.MAX_ENTRIES = saved


def test_lying_size_header_rejected(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    info = zipfile.ZipInfo("liar.bin")
    zf = _zf([(info, b"A" * 1000)])
    zf.getinfo("liar.bin").file_size = 10  # declared < actual
    with pytest.raises(OpError):
        _run(zf, t, s)
```

- [ ] **Step 2: Run to verify failure** — FAIL, module missing.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/extract.py`:

```python
import os
import re
import shutil
import stat

from .errors import OpError

MAX_ENTRIES = 10_000
MAX_TOTAL_BYTES = 4 * 1024 ** 3
CHUNK = 65536
MARKER = "EXTRACT_TO_GAME_FOLDER"

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _normalize(name):
    return name.replace("\\", "/")


def _is_unsafe(name):
    return (name.startswith("/") or _DRIVE_RE.match(name) is not None
            or any(seg == ".." for seg in name.split("/")))


def _is_symlink(info):
    return stat.S_ISLNK(info.external_attr >> 16)


def _resolve_case(root, relpath):
    """Map relpath onto the existing tree case-insensitively (ext4 is case-sensitive;
    a case-mismatched duplicate tree means the DLL never loads)."""
    cur = root
    for part in [p for p in relpath.split("/") if p]:
        if os.path.isdir(cur):
            entries = os.listdir(cur)
            if part in entries:
                chosen = part
            else:
                matches = [e for e in entries if e.lower() == part.lower()]
                if len(matches) > 1:
                    raise OpError("extract_failed", f"ambiguous case variants for {part!r}")
                chosen = matches[0] if matches else part
            cur = os.path.join(cur, chosen)
        else:
            if os.path.isfile(cur):
                raise OpError("extract_failed", f"file blocks directory path: {cur}")
            cur = os.path.join(cur, part)
    return cur


def safe_extract(zf, target_dir, staging_dir, owned_files=frozenset(), backup_dir=None):
    """Extract zf into target_dir with zip-slip/symlink/bomb guards.

    owned_files: relpaths the current install manifest owns (never pristine-backed-up).
    backup_dir: write-once pristine backups of overwritten non-owned files.
    Returns (written_relpaths, newly_backed_up_relpaths). Rolls back on failure.
    """
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise OpError("extract_failed", "archive has too many entries")
    if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise OpError("extract_failed", "archive too large")

    real_target = os.path.realpath(target_dir)
    written = []          # (relpath, dest, staged_copy_or_None)
    newly_backed = []
    total_written = 0
    try:
        for info in infos:
            name = _normalize(info.filename)
            if not name or name.endswith("/"):
                continue
            if os.path.basename(name) == MARKER:
                continue
            if _is_unsafe(name):
                raise OpError("extract_failed", f"unsafe path in archive: {name!r}")
            if _is_symlink(info):
                continue

            dest = _resolve_case(real_target, name)
            real_dest = os.path.realpath(dest)
            if os.path.commonpath([real_target, real_dest]) != real_target:
                raise OpError("extract_failed", f"path escapes game dir: {name!r}")
            rel = os.path.relpath(real_dest, real_target)

            os.makedirs(os.path.dirname(dest) or dest, exist_ok=True)
            staged = None
            if os.path.exists(dest):
                staged = os.path.join(staging_dir, rel)
                os.makedirs(os.path.dirname(staged), exist_ok=True)
                shutil.copy2(dest, staged)
                if backup_dir is not None and rel not in owned_files:
                    bpath = os.path.join(backup_dir, rel)
                    if not os.path.exists(bpath):
                        os.makedirs(os.path.dirname(bpath), exist_ok=True)
                        shutil.copy2(dest, bpath)
                        newly_backed.append(rel)

            with zf.open(info) as src, open(dest, "wb") as out:
                while True:
                    chunk = src.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    total_written += len(chunk)
                    if out.tell() > info.file_size:
                        raise OpError("extract_failed", f"size header mismatch: {name!r}")
                    if total_written > MAX_TOTAL_BYTES:
                        raise OpError("extract_failed", "archive too large")
            written.append((rel, dest, staged))
        return [w[0] for w in written], newly_backed
    except Exception as exc:
        for _, dest, staged in reversed(written):
            try:
                if staged is not None:
                    shutil.copy2(staged, dest)
                elif os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
        if isinstance(exc, OpError):
            raise
        raise OpError("extract_failed") from exc
```

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_extract.py -v` → all PASS (11 tests).

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: hardened zip extractor with rollback and pristine backups"`

---

### Task 6: `manifest.py` — install records

**Files:**
- Create: `py_modules/lyall_core/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_manifest.py`:

```python
from lyall_core import manifest


def test_build_save_load_roundtrip(tmp_path):
    m = manifest.build(mod_id="FooFix", appid=42, version="0.0.1", sha256="0" * 64,
                       install_path="/g", target_dir="/g/Bin", files=["a.dll"],
                       backed_up_files=[], wine_dll_override="dsound",
                       launch_option_handled="dlo", installed_at="t0")
    assert m["schema"] == 1
    manifest.save(str(tmp_path), m)
    assert manifest.load(str(tmp_path), 42, "FooFix") == m
    assert manifest.load(str(tmp_path), 42, "Other") is None


def test_apply_update_carries_backups_and_reports_stale(tmp_path):
    old = manifest.build(mod_id="F", appid=1, version="1", sha256="a" * 64,
                         install_path="/g", target_dir="/g", files=["a.dll", "gone.dll"],
                         backed_up_files=["orig.ini"], wine_dll_override="dsound",
                         launch_option_handled="dlo", installed_at="t0")
    new, stale = manifest.apply_update(old, files=["a.dll", "new.dll"], version="2",
                                       sha256="b" * 64, newly_backed_up=["another.ini"],
                                       installed_at="t1")
    assert stale == ["gone.dll"]
    assert new["version"] == "2"
    assert sorted(new["backed_up_files"]) == ["another.ini", "orig.ini"]


def test_load_all_and_prune_orphans(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    live = manifest.build(mod_id="Live", appid=1, version="1", sha256="a" * 64,
                          install_path=str(game_dir), target_dir=str(game_dir),
                          files=[], backed_up_files=[], wine_dll_override="dsound",
                          launch_option_handled="dlo", installed_at="t")
    orphan = manifest.build(mod_id="Orphan", appid=2, version="1", sha256="a" * 64,
                            install_path=str(tmp_path / "deleted-game"),
                            target_dir=str(tmp_path / "deleted-game"),
                            files=[], backed_up_files=[], wine_dll_override="dsound",
                            launch_option_handled="dlo", installed_at="t")
    manifest.save(str(tmp_path), live)
    manifest.save(str(tmp_path), orphan)
    removed = manifest.prune_orphans(str(tmp_path))
    assert removed == [(2, "Orphan")]
    assert [m["mod_id"] for m in manifest.load_all(str(tmp_path))] == ["Live"]
```

- [ ] **Step 2: Run to verify failure** — FAIL.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/manifest.py`:

```python
import json
import os
import shutil

SCHEMA = 1


def _installs_dir(runtime_dir):
    return os.path.join(runtime_dir, "installs")


def path_for(runtime_dir, appid, mod_id):
    return os.path.join(_installs_dir(runtime_dir), f"{appid}-{mod_id}.json")


def backup_dir_for(runtime_dir, appid, mod_id):
    return os.path.join(runtime_dir, "backups", f"{appid}-{mod_id}")


def build(*, mod_id, appid, version, sha256, install_path, target_dir, files,
          backed_up_files, wine_dll_override, launch_option_handled, installed_at):
    return {
        "schema": SCHEMA, "mod_id": mod_id, "appid": appid, "version": version,
        "sha256": sha256, "install_path": install_path, "target_dir": target_dir,
        "files": list(files), "backed_up_files": list(backed_up_files),
        "wine_dll_override": wine_dll_override,
        "launch_option_handled": launch_option_handled, "installed_at": installed_at,
    }


def apply_update(old, *, files, version, sha256, newly_backed_up, installed_at):
    """New manifest for an update: carries pristine backups forward; returns files
    from the old release that the new one no longer ships (caller deletes them)."""
    stale = [f for f in old["files"] if f not in set(files)]
    new = dict(old)
    new.update(version=version, sha256=sha256, files=list(files), installed_at=installed_at,
               backed_up_files=sorted(set(old["backed_up_files"]) | set(newly_backed_up)))
    return new, stale


def save(runtime_dir, m):
    os.makedirs(_installs_dir(runtime_dir), exist_ok=True)
    with open(path_for(runtime_dir, m["appid"], m["mod_id"]), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)


def load(runtime_dir, appid, mod_id):
    try:
        with open(path_for(runtime_dir, appid, mod_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_all(runtime_dir):
    out = []
    d = _installs_dir(runtime_dir)
    if not os.path.isdir(d):
        return out
    for entry in sorted(os.listdir(d)):
        if entry.endswith(".json"):
            try:
                with open(os.path.join(d, entry), encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, ValueError):
                continue
    return out


def remove(runtime_dir, appid, mod_id):
    try:
        os.remove(path_for(runtime_dir, appid, mod_id))
    except OSError:
        pass
    shutil.rmtree(backup_dir_for(runtime_dir, appid, mod_id), ignore_errors=True)


def prune_orphans(runtime_dir):
    """Drop manifests whose game install dir is gone (game uninstalled — Steam removed
    the whole dir, so restoration is meaningless). Returns [(appid, mod_id)] removed."""
    removed = []
    for m in load_all(runtime_dir):
        if not os.path.isdir(m["install_path"]):
            remove(runtime_dir, m["appid"], m["mod_id"])
            removed.append((m["appid"], m["mod_id"]))
    return removed
```

- [ ] **Step 4: Run** — all PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: install manifests with update/prune semantics"`

---

### Task 7: `procs.py` + `dlo.py`

**Files:**
- Create: `py_modules/lyall_core/procs.py`, `py_modules/lyall_core/dlo.py`
- Test: `tests/test_procs_dlo.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_procs_dlo.py`:

```python
import json

from lyall_core import dlo, procs


def test_game_running_detects_cmdline(tmp_path):
    proc = tmp_path / "1234"
    proc.mkdir()
    (proc / "cmdline").write_bytes(b"/g/steamapps/common/Expedition 33/x.exe\x00-arg\x00")
    assert procs.game_running("/g/steamapps/common/Expedition 33", proc_root=str(tmp_path))
    assert not procs.game_running("/g/steamapps/common/Other", proc_root=str(tmp_path))


def _settings(state=None, registered=True):
    return json.dumps({
        "launchOptions": [{"id": "lyall-FooFix"}] if registered else [],
        "profiles": {"42": {"state": state or {}}},
    })


def test_override_status_states():
    assert dlo.override_status(_settings(registered=False), "FooFix", 42) == "not_registered"
    assert dlo.override_status(_settings(), "FooFix", 42) == "registered_disabled"
    assert dlo.override_status(_settings(state={"lyall-FooFix": True}), "FooFix", 42) == "registered_enabled"


def test_override_status_degrades_to_unknown():
    assert dlo.override_status(None, "FooFix", 42) == "unknown"
    assert dlo.override_status("not json{", "FooFix", 42) == "unknown"
    assert dlo.override_status(json.dumps([1, 2]), "FooFix", 42) == "unknown"
```

- [ ] **Step 2: Run to verify failure** — FAIL.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/procs.py`:

```python
import os


def game_running(install_path, proc_root="/proc"):
    """True if any process cmdline references the game's install path."""
    needle = install_path.encode()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return False
    for pid in pids:
        try:
            with open(os.path.join(proc_root, pid, "cmdline"), "rb") as f:
                if needle in f.read():
                    return True
        except OSError:
            continue
    return False
```

`py_modules/lyall_core/dlo.py`:

```python
import json
import os

# ~/.dlo/settings.json is DLO-internal state (verified at v1.12), NOT a contract.
# Anything unexpected must degrade to "unknown"; "unknown" never surfaces warnings.


def settings_path(user_home):
    return os.path.join(user_home, ".dlo", "settings.json")


def read_settings_text(user_home):
    try:
        with open(settings_path(user_home), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def override_status(settings_text, mod_id, appid):
    if settings_text is None:
        return "unknown"
    try:
        data = json.loads(settings_text)
        option_id = f"lyall-{mod_id}"
        options = data.get("launchOptions") or []
        if not any(o.get("id") == option_id for o in options):
            return "not_registered"
        profile = (data.get("profiles") or {}).get(str(appid)) or {}
        state = profile.get("state") or {}
        return "registered_enabled" if state.get(option_id) else "registered_disabled"
    except (ValueError, AttributeError, TypeError):
        return "unknown"
```

- [ ] **Step 4: Run** — all PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: running-game guard and DLO override-status probe"`

---

### Task 8: `installer.py` — download-verify-extract-record, uninstall

**Files:**
- Create: `py_modules/lyall_core/installer.py`
- Test: `tests/test_installer.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_installer.py`:

```python
import hashlib
import io
import zipfile

import pytest

from lyall_core import installer, manifest
from lyall_core.errors import OpError


def _zip_blob(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def _mod(blob, layout="flat", subdir="Bin"):
    return {
        "games": [{"steam_appid": 42, **({"install_subdir": subdir} if subdir else {})}],
        "wine_dll_override": "dsound", "loader": "ual", "zip_layout": layout,
        "derived_release": "0.0.1",
        "download_url": "https://codeberg.org/x/F.zip",
        "sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob),
    }


def _stream(blob):
    async def stream(url):
        yield blob[: len(blob) // 2]
        yield blob[len(blob) // 2:]
    return stream


async def _install(tmp_path, blob, mod, game_running=lambda p: False):
    game = tmp_path / "game"
    game.mkdir(exist_ok=True)
    paths = installer.Paths(runtime_dir=str(tmp_path / "runtime"))
    return await installer.install(
        mod_id="FooFix", mod=mod, appid=42, install_path=str(game), paths=paths,
        open_stream=_stream(blob), progress=lambda phase, pct: None,
        game_running=game_running, now=lambda: "t0"), game


async def test_install_flat_with_subdir(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a", "dsound.dll": b"d"})
    m, game = await _install(tmp_path, blob, _mod(blob))
    assert (game / "Bin/dsound.dll").exists()
    assert m["version"] == "0.0.1" and m["target_dir"].endswith("/Bin")
    assert sorted(m["files"]) == ["Fix.asi", "dsound.dll"]


async def test_install_pathed_to_root(tmp_path):
    blob = _zip_blob({"End/Binaries/Win64/dsound.dll": b"d"})
    m, game = await _install(tmp_path, blob, _mod(blob, layout="pathed", subdir=None))
    assert (game / "End/Binaries/Win64/dsound.dll").exists()


async def test_flat_without_subdir_blocked(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, _mod(blob, subdir=None))
    assert e.value.code == "needs_curation"


async def test_bad_hash_rejected(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    mod = _mod(blob)
    mod["sha256"] = "f" * 64
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, mod)
    assert e.value.code == "verify_failed"


async def test_game_running_blocks_before_download(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, _mod(blob), game_running=lambda p: True)
    assert e.value.code == "game_running"


async def test_update_deletes_stale_and_uninstall_restores(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "Bin").mkdir()
    (game / "Bin/game.ini").write_bytes(b"original")  # pristine, will be overwritten

    v1 = _zip_blob({"Fix.asi": b"1", "gone.dll": b"1", "game.ini": b"mod1"})
    paths = installer.Paths(runtime_dir=str(tmp_path / "runtime"))

    async def run(blob, mod):
        return await installer.install(mod_id="FooFix", mod=mod, appid=42,
                                       install_path=str(game), paths=paths,
                                       open_stream=_stream(blob),
                                       progress=lambda *a: None,
                                       game_running=lambda p: False, now=lambda: "t")

    await run(v1, _mod(v1))
    v2 = _zip_blob({"Fix.asi": b"2", "game.ini": b"mod2"})
    mod2 = _mod(v2)
    mod2["derived_release"] = "0.0.2"
    m2 = await run(v2, mod2)
    assert not (game / "Bin/gone.dll").exists()          # stale file removed
    assert m2["backed_up_files"] == ["game.ini"]          # pristine backup carried

    installer.uninstall(paths, appid=42, mod_id="FooFix")
    assert not (game / "Bin/Fix.asi").exists()
    assert (game / "Bin/game.ini").read_bytes() == b"original"
    assert manifest.load(paths.runtime_dir, 42, "FooFix") is None
```

- [ ] **Step 2: Run to verify failure** — FAIL. (Note the first test shows the sync-wrapper form; with `asyncio_mode = auto` the plain `async def` tests run directly — prefer that form for all of them.)

- [ ] **Step 3: Implement**

`py_modules/lyall_core/installer.py`:

```python
import hashlib
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass

from . import manifest
from .errors import OpError
from .extract import safe_extract


@dataclass
class Paths:
    runtime_dir: str

    def __post_init__(self):
        self.downloads = os.path.join(self.runtime_dir, "downloads")
        self.staging = os.path.join(self.runtime_dir, "staging")
        for d in (self.downloads, self.staging):
            os.makedirs(d, exist_ok=True)


def target_dir_for(mod, appid, install_path):
    game = next((g for g in mod.get("games", []) if g.get("steam_appid") == appid), None)
    if game is None:
        raise OpError("not_found")
    if mod["zip_layout"] == "pathed":
        return install_path
    subdir = game.get("install_subdir")
    if not subdir:
        raise OpError("needs_curation")
    return os.path.join(install_path, subdir)


async def download_verified(open_stream, mod, dest, progress):
    """Stream the pinned asset to dest, verifying size and sha256 as bytes arrive."""
    h = hashlib.sha256()
    total = 0
    with open(dest, "wb") as f:
        async for chunk in open_stream(mod["download_url"]):
            total += len(chunk)
            if total > mod["size"]:
                break
            h.update(chunk)
            f.write(chunk)
            progress("download", int(total * 100 / mod["size"]))
    if total != mod["size"] or h.hexdigest() != mod["sha256"]:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise OpError("verify_failed")


async def install(*, mod_id, mod, appid, install_path, paths, open_stream, progress,
                  game_running, now):
    if game_running(install_path):
        raise OpError("game_running")
    target_dir = target_dir_for(mod, appid, install_path)
    os.makedirs(target_dir, exist_ok=True)

    zip_path = os.path.join(paths.downloads, f"{mod_id}-{mod['derived_release']}.zip")
    await download_verified(open_stream, mod, zip_path, progress)

    old = manifest.load(paths.runtime_dir, appid, mod_id)
    owned = set(old["files"]) if old else set()
    backup_dir = manifest.backup_dir_for(paths.runtime_dir, appid, mod_id)
    staging = tempfile.mkdtemp(dir=paths.staging)
    try:
        progress("extract", None)
        with zipfile.ZipFile(zip_path) as zf:
            written, newly_backed = safe_extract(zf, target_dir, staging,
                                                 owned_files=owned, backup_dir=backup_dir)
        if old:
            m, stale = manifest.apply_update(old, files=written,
                                             version=mod["derived_release"],
                                             sha256=mod["sha256"],
                                             newly_backed_up=newly_backed,
                                             installed_at=now())
            for rel in stale:
                try:
                    os.remove(os.path.join(old["target_dir"], rel))
                except OSError:
                    pass
        else:
            m = manifest.build(mod_id=mod_id, appid=appid, version=mod["derived_release"],
                               sha256=mod["sha256"], install_path=install_path,
                               target_dir=target_dir, files=written,
                               backed_up_files=newly_backed,
                               wine_dll_override=mod["wine_dll_override"],
                               launch_option_handled="manual_pending",
                               installed_at=now())
        manifest.save(paths.runtime_dir, m)
        return m
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            os.remove(zip_path)
        except OSError:
            pass


def uninstall(paths, *, appid, mod_id):
    m = manifest.load(paths.runtime_dir, appid, mod_id)
    if m is None:
        raise OpError("not_found")
    for rel in m["files"]:
        try:
            os.remove(os.path.join(m["target_dir"], rel))
        except OSError:
            pass
    backup_dir = manifest.backup_dir_for(paths.runtime_dir, appid, mod_id)
    for rel in m["backed_up_files"]:
        src = os.path.join(backup_dir, rel)
        dst = os.path.join(m["target_dir"], rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    manifest.remove(paths.runtime_dir, appid, mod_id)
    return m
```

(`launch_option_handled` starts as `"manual_pending"`; the frontend flips it to `"dlo"` via `set_launch_option_handled` after a successful DLO dispatch — added in Task 9.)

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_installer.py -v` → all PASS. Full suite: `python3 -m pytest -q` → all PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: installer with pinned verified downloads, update and uninstall"`

---

### Task 9: `ops.py` + `state.py` + `main.py` glue

**Files:**
- Create: `py_modules/lyall_core/ops.py`, `py_modules/lyall_core/state.py`, `main.py`
- Test: `tests/test_ops_state.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_ops_state.py`:

```python
import pytest

from lyall_core import ops as ops_mod, state
from lyall_core.errors import OpError


def test_ops_one_per_appid():
    ops = ops_mod.Ops()
    ops.start(42, "install", "FooFix")
    with pytest.raises(OpError) as e:
        ops.start(42, "uninstall", "OtherFix")
    assert e.value.code == "already_in_progress"
    ops.finish(42)
    ops.start(42, "uninstall", "FooFix")  # ok after finish


async def test_run_operation_emits_done_and_clears():
    ops = ops_mod.Ops()
    events = []

    async def emit(name, *args):
        events.append((name, args))

    async def work_ok():
        return {"wine_dll_override": "dsound", "loader": "ual"}

    ops.start(42, "install", "FooFix")
    await ops_mod.run_operation(ops, 42, "install", "FooFix", work_ok, emit, log=print)
    assert events == [("qf_done", ("install", "FooFix", 42, True, "", "dsound", "ual"))]
    assert ops.get(42) is None

    async def work_fail():
        raise OpError("verify_failed")

    ops.start(42, "install", "FooFix")
    await ops_mod.run_operation(ops, 42, "install", "FooFix", work_fail, emit, log=print)
    assert events[-1] == ("qf_done", ("install", "FooFix", 42, False, "verify_failed", "", ""))


def _rows(**kw):
    mods = {"FooFix": {
        "games": [{"steam_appid": 42, "install_subdir": "Bin"}],
        "wine_dll_override": "dsound", "loader": "ual", "zip_layout": "flat",
        "derived_release": "0.0.2",
    }}
    installed = {42: {"name": "Game", "install_path": "/g"}}
    defaults = dict(mods=mods, installed=installed, manifests=[],
                    dlo_text=None, busy_map={})
    defaults.update(kw)
    return state.build_rows(**defaults)


def test_row_not_installed():
    rows = _rows()
    assert rows[0]["status"] == "not_installed"
    assert rows[0]["override_status"] == "unknown"


def test_row_update_available_and_busy():
    man = {"schema": 1, "mod_id": "FooFix", "appid": 42, "version": "0.0.1",
           "files": [], "backed_up_files": [], "install_path": "/g", "target_dir": "/g/Bin",
           "sha256": "0" * 64, "wine_dll_override": "dsound",
           "launch_option_handled": "dlo", "installed_at": "t"}
    rows = _rows(manifests=[man], busy_map={42: {"op": "install", "phase": "download", "pct": 10}})
    assert rows[0]["status"] == "update_available"
    assert rows[0]["installed_version"] == "0.0.1"
    assert rows[0]["busy"]["phase"] == "download"


def test_row_needs_curation_and_blocked_by():
    mods = {
        "NoSub": {"games": [{"steam_appid": 42}], "wine_dll_override": "dsound",
                   "loader": "ual", "zip_layout": "flat", "derived_release": "1"},
        "Installed": {"games": [{"steam_appid": 42, "install_subdir": "Bin"}],
                       "wine_dll_override": "winmm", "loader": "ual",
                       "zip_layout": "flat", "derived_release": "1"},
    }
    man = {"schema": 1, "mod_id": "Installed", "appid": 42, "version": "1", "files": [],
           "backed_up_files": [], "install_path": "/g", "target_dir": "/g/Bin",
           "sha256": "0" * 64, "wine_dll_override": "winmm",
           "launch_option_handled": "dlo", "installed_at": "t"}
    rows = state.build_rows(mods=mods, installed={42: {"name": "G", "install_path": "/g"}},
                            manifests=[man], dlo_text=None, busy_map={})
    by_mod = {r["mod_id"]: r for r in rows}
    assert by_mod["NoSub"]["status"] == "needs_curation"
    assert by_mod["NoSub"]["blocked_by"] == "Installed"
    assert by_mod["Installed"]["status"] == "installed"
```

- [ ] **Step 2: Run to verify failure** — FAIL.

- [ ] **Step 3: Implement**

`py_modules/lyall_core/ops.py`:

```python
from .errors import OpError


class Ops:
    """One operation per appid. In-memory only: a plugin restart clears it;
    disk consistency comes from the installer's rollback."""

    def __init__(self):
        self._table = {}

    def start(self, appid, op, mod_id):
        if appid in self._table:
            raise OpError("already_in_progress")
        self._table[appid] = {"op": op, "mod_id": mod_id, "phase": "starting", "pct": None}

    def progress(self, appid, phase, pct):
        if appid in self._table:
            self._table[appid].update(phase=phase, pct=pct)

    def finish(self, appid):
        self._table.pop(appid, None)

    def get(self, appid):
        return self._table.get(appid)

    def busy_map(self):
        return dict(self._table)


async def run_operation(ops, appid, op, mod_id, work, emit, log):
    """Run an already-started operation to completion; always emits qf_done and frees the slot."""
    try:
        result = await work()
        await emit("qf_done", op, mod_id, appid, True, "",
                   result.get("wine_dll_override", ""), result.get("loader", ""))
    except OpError as e:
        await emit("qf_done", op, mod_id, appid, False, e.code, "", "")
    except Exception as e:  # noqa: BLE001 — must never leak across the bridge
        log(f"unexpected error in {op} {mod_id}/{appid}: {e!r}")
        await emit("qf_done", op, mod_id, appid, False, "unexpected", "", "")
    finally:
        ops.finish(appid)
```

`py_modules/lyall_core/state.py`:

```python
from . import dlo


def build_rows(*, mods, installed, manifests, dlo_text, busy_map):
    """Rows for every (usable mod, installed game) pair.

    Status precedence: update_available > needs_launch_option > installed;
    needs_curation for flat mods without install_subdir; blocked_by names another
    mod already installed for the same game (two mods must not share a game dir).
    """
    by_key = {(m["appid"], m["mod_id"]): m for m in manifests}
    installed_mod_for_appid = {m["appid"]: m["mod_id"] for m in manifests}
    rows = []
    for mod_id, mod in mods.items():
        for game in mod.get("games", []):
            appid = game.get("steam_appid")
            inst = installed.get(appid)
            if not inst:
                continue
            man = by_key.get((appid, mod_id))
            latest = mod.get("derived_release")
            other = installed_mod_for_appid.get(appid)
            blocked_by = other if (man is None and other) else None

            if man is not None:
                if man["version"] != latest:
                    status = "update_available"
                elif man.get("launch_option_handled") == "manual_pending":
                    status = "needs_launch_option"
                else:
                    status = "installed"
            elif mod["zip_layout"] == "flat" and not game.get("install_subdir"):
                status = "needs_curation"
            else:
                status = "not_installed"

            rows.append({
                "appid": appid, "mod_id": mod_id, "name": inst["name"],
                "install_path": inst["install_path"],
                "installed_version": man["version"] if man else None,
                "latest_version": latest,
                "wine_dll_override": mod["wine_dll_override"], "loader": mod["loader"],
                "status": status,
                "override_status": dlo.override_status(dlo_text, mod_id, appid),
                "busy": busy_map.get(appid), "blocked_by": blocked_by,
            })
    return rows
```

`main.py`:

```python
import asyncio
import json
import ssl
from datetime import datetime, timezone

import aiohttp
import certifi

import decky  # noqa: F401 — injected by Decky Loader
from lyall_core import catalog, dlo, installer, manifest, ops as ops_mod, procs, state
from lyall_core.errors import OpError, fail, ok

SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _open_stream(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=SSL_CTX) as resp:
            resp.raise_for_status()
            async for chunk in resp.content.iter_chunked(65536):
                yield chunk


class Plugin:
    async def _main(self):
        self.loop = asyncio.get_event_loop()
        self.ops = ops_mod.Ops()
        self.paths = installer.Paths(runtime_dir=decky.DECKY_PLUGIN_RUNTIME_DIR)
        self.settings_dir = decky.DECKY_PLUGIN_SETTINGS_DIR
        self.mods, self.catalog_updated_at = {}, None
        raw, fetched_at = catalog.load_cache(self.settings_dir)
        if raw:
            self._adopt_catalog(raw, fetched_at)
        self.loop.create_task(self._fetch_catalog())
        decky.logger.info("Lyall Fixes loaded")

    def _adopt_catalog(self, raw, fetched_at):
        usable, skipped = catalog.usable_mods(raw)
        self.mods, self.catalog_updated_at = usable, fetched_at
        for mod_id, problems in skipped.items():
            decky.logger.warning(f"skipping catalog entry {mod_id}: {problems}")

    async def _fetch_catalog(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(catalog.CATALOG_URL, ssl=SSL_CTX) as resp:
                    resp.raise_for_status()
                    raw = json.loads(await resp.text())
            fetched_at = _now()
            catalog.save_cache(self.settings_dir, raw, fetched_at)
            self._adopt_catalog(raw, fetched_at)
            return True
        except Exception as e:
            decky.logger.warning(f"catalog fetch failed: {e!r}")
            return False

    def _installed_games(self):
        from lyall_core import steam as steam_mod
        if getattr(self, "_steam_root", None) is None:
            self._steam_root = steam_mod.find_steam_root(decky.DECKY_USER_HOME)
        return steam_mod.installed_games(self._steam_root) if self._steam_root else {}

    def _state(self):
        installed = self._installed_games()
        rows = state.build_rows(
            mods=self.mods, installed=installed,
            manifests=manifest.load_all(self.paths.runtime_dir),
            dlo_text=dlo.read_settings_text(decky.DECKY_USER_HOME),
            busy_map=self.ops.busy_map())
        return ok(catalog_updated_at=self.catalog_updated_at, games=rows)

    async def get_state(self):
        try:
            return self._state()
        except Exception as e:
            decky.logger.exception("get_state failed")
            return fail("unexpected", str(e)[:60])

    async def refresh(self):
        try:
            fetched = await self._fetch_catalog()
            manifest.prune_orphans(self.paths.runtime_dir)
            if not fetched:
                result = self._state()
                result.update(code="network_offline",
                              message="No connection — using cached data")
                return result
            return self._state()
        except Exception:
            decky.logger.exception("refresh failed")
            return fail("unexpected")

    async def install(self, mod_id, appid):
        return self._start_op("install", mod_id, appid)

    async def uninstall(self, mod_id, appid):
        return self._start_op("uninstall", mod_id, appid)

    async def set_launch_option_handled(self, mod_id, appid, value):
        try:
            m = manifest.load(self.paths.runtime_dir, appid, mod_id)
            if m is None:
                return fail("not_found")
            m["launch_option_handled"] = value
            manifest.save(self.paths.runtime_dir, m)
            return ok()
        except Exception:
            decky.logger.exception("set_launch_option_handled failed")
            return fail("unexpected")

    def _start_op(self, op, mod_id, appid):
        try:
            mod = self.mods.get(mod_id)
            if op == "install":
                if mod is None:
                    return fail("not_found")
                game = self._installed_games().get(appid)
                if game is None:
                    return fail("not_found")

                async def work():
                    return await installer.install(
                        mod_id=mod_id, mod=mod, appid=appid,
                        install_path=game["install_path"], paths=self.paths,
                        open_stream=_open_stream,
                        progress=lambda phase, pct: self._progress(appid, phase, pct),
                        game_running=procs.game_running, now=_now)
            else:
                async def work():
                    m = manifest.load(self.paths.runtime_dir, appid, mod_id)
                    if m and procs.game_running(m["install_path"]):
                        raise OpError("game_running")
                    return installer.uninstall(self.paths, appid=appid, mod_id=mod_id)

            self.ops.start(appid, op, mod_id)
            self.loop.create_task(ops_mod.run_operation(
                self.ops, appid, op, mod_id, work, decky.emit, decky.logger.error))
            return ok(accepted=True)
        except OpError as e:
            return fail(e.code, e.message)
        except Exception:
            decky.logger.exception(f"{op} failed to start")
            return fail("unexpected")

    def _progress(self, appid, phase, pct):
        self.ops.progress(appid, phase, pct)
        self.loop.create_task(decky.emit("qf_progress",
                                         self.ops.get(appid)["mod_id"] if self.ops.get(appid) else "",
                                         appid, phase, pct))

    async def _unload(self):
        decky.logger.info("Lyall Fixes unloading")

    async def _uninstall(self):
        # Installed fixes, manifests, and DLO options stay — removing mods from game
        # dirs on plugin uninstall would be surprising and unrecoverable (documented in README).
        decky.logger.info("Lyall Fixes uninstalled; installed fixes left in place")
```

- [ ] **Step 4: Run** — `python3 -m pytest -q` → all PASS (main.py is not imported by tests). Also sanity-compile: `python3 -c "import ast; ast.parse(open('main.py').read())" && echo OK`.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: operations table, state rows, and Decky plugin glue"`

---

### Task 10: Frontend libs — API bindings, launch options, sorting

**Files:**
- Create: `src/api.ts`, `src/lib/launchOptions.ts`, `src/lib/sort.ts`
- Test: `src/lib/__tests__/launchOptions.test.ts`, `src/lib/__tests__/sort.test.ts`

- [ ] **Step 1: Write the failing tests**

`src/lib/__tests__/launchOptions.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { dloPayload, manualLaunchOption } from "../launchOptions";

describe("launchOptions", () => {
  it("builds a stable DLO payload", () => {
    expect(dloPayload("ClairObscurFix", "dsound")).toEqual([{
      id: "lyall-ClairObscurFix",
      group: "Lyall Fixes",
      name: "ClairObscurFix (dsound override)",
      on: 'WINEDLLOVERRIDES="dsound=n,b"',
      off: "",
      enableGlobally: false,
    }]);
  });

  it("builds the manual launch option line with lowercase %command%", () => {
    expect(manualLaunchOption("winmm")).toBe('WINEDLLOVERRIDES="winmm=n,b" %command%');
  });
});
```

`src/lib/__tests__/sort.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { sortRows } from "../sort";
import type { GameRow } from "../../api";

const row = (over: Partial<GameRow>): GameRow => ({
  appid: 1, mod_id: "M", name: "G", install_path: "/g",
  installed_version: null, latest_version: "1",
  wine_dll_override: "dsound", loader: "ual",
  status: "not_installed", override_status: "unknown",
  busy: null, blocked_by: null, ...over,
});

describe("sortRows", () => {
  it("orders busy > update > warning > installed > not_installed > needs_curation", () => {
    const rows = [
      row({ mod_id: "curation", status: "needs_curation" }),
      row({ mod_id: "plain", status: "installed", override_status: "registered_enabled" }),
      row({ mod_id: "warn", status: "installed", override_status: "registered_disabled" }),
      row({ mod_id: "manual", status: "needs_launch_option" }),
      row({ mod_id: "upd", status: "update_available" }),
      row({ mod_id: "busy", busy: { op: "install", phase: "download", pct: 5 } }),
      row({ mod_id: "not", status: "not_installed" }),
    ];
    expect(sortRows(rows).map(r => r.mod_id))
      .toEqual(["busy", "upd", "manual", "warn", "plain", "not", "curation"]);
  });
});
```

- [ ] **Step 2: Run to verify failure** — `pnpm run test` → FAIL (modules missing).

- [ ] **Step 3: Implement**

`src/api.ts`:

```ts
import { callable } from "@decky/api";

export type Status = "not_installed" | "installed" | "update_available"
  | "needs_curation" | "needs_launch_option" | "unknown";
export type OverrideStatus = "registered_enabled" | "registered_disabled"
  | "not_registered" | "unknown";

export interface Busy { op: "install" | "uninstall"; phase: string; pct: number | null }

export interface GameRow {
  appid: number; mod_id: string; name: string; install_path: string;
  installed_version: string | null; latest_version: string | null;
  wine_dll_override: string; loader: string;
  status: Status; override_status: OverrideStatus;
  busy: Busy | null; blocked_by: string | null;
}

export interface StateResult {
  ok: boolean; code?: string; message?: string;
  catalog_updated_at?: string | null; games?: GameRow[];
}
export interface OpResult { ok: boolean; accepted?: boolean; code?: string; message?: string }

export const getState = callable<[], StateResult>("get_state");
export const refresh = callable<[], StateResult>("refresh");
export const installMod = callable<[mod_id: string, appid: number], OpResult>("install");
export const uninstallMod = callable<[mod_id: string, appid: number], OpResult>("uninstall");
export const setLaunchOptionHandled =
  callable<[mod_id: string, appid: number, value: string], OpResult>("set_launch_option_handled");
```

`src/lib/launchOptions.ts`:

```ts
export const DLO_EVENT = "dlo-add-launch-options";

export const dloPayload = (modId: string, dll: string) => [{
  id: `lyall-${modId}`,           // stable id → re-dispatch upserts, never duplicates
  group: "Lyall Fixes",
  name: `${modId} (${dll} override)`,
  on: `WINEDLLOVERRIDES="${dll}=n,b"`,  // env-only; DLO merges WINEDLLOVERRIDES with ';'
  off: "",
  enableGlobally: false,
}];

export const manualLaunchOption = (dll: string) =>
  `WINEDLLOVERRIDES="${dll}=n,b" %command%`;

// Read live on every use — DLO may load after us or be installed later.
export const hasDLO = () => (window as any).hasDeckyLaunchOptions === true;

export const dispatchDlo = (modId: string, dll: string) =>
  window.dispatchEvent(new CustomEvent(DLO_EVENT, { detail: dloPayload(modId, dll) }));
```

`src/lib/sort.ts`:

```ts
import type { GameRow } from "../api";

function rank(row: GameRow): number {
  if (row.busy) return 0;
  if (row.status === "update_available") return 1;
  const overrideWarning = row.override_status === "not_registered"
    || row.override_status === "registered_disabled";
  if (row.status === "needs_launch_option") return 2;
  if (row.status === "installed" && overrideWarning) return 2;
  if (row.status === "installed") return 3;
  if (row.status === "not_installed") return 4;
  if (row.status === "needs_curation") return 5;
  return 6;
}

export function sortRows(rows: GameRow[]): GameRow[] {
  return [...rows].sort((a, b) =>
    rank(a) - rank(b) || a.name.localeCompare(b.name) || a.mod_id.localeCompare(b.mod_id));
}
```

- [ ] **Step 4: Run** — `pnpm run test` → all PASS. (`api.ts` imports `@decky/api` which vitest must not execute — `sort.test.ts` only imports the type, which erases at compile time; if vitest still chokes, move `GameRow` into `src/types.ts` and re-export from `api.ts`.)

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: frontend api bindings, DLO payloads, row sorting"`

---### Task 11: Frontend UI — panel, rows, modals, event wiring

**Files:**
- Create: `src/store.ts`, `src/components/Panel.tsx`, `src/components/GameRowItem.tsx`, `src/components/PostInstallModal.tsx`, `src/components/ManualLaunchOptionModal.tsx`
- Modify: `src/index.tsx`

- [ ] **Step 1: Implement the pieces** (UI code — verified by build + on-device test, no unit tests)

`src/store.ts` (tiny external store so events reach a remounting panel):

```ts
import type { Busy } from "./api";

type Listener = () => void;
const listeners = new Set<Listener>();
export const progressByAppid = new Map<number, Busy>();
let stateDirty = 0;

export function setProgress(appid: number, busy: Busy | null) {
  if (busy) progressByAppid.set(appid, busy);
  else progressByAppid.delete(appid);
  notify();
}
export function markStateDirty() { stateDirty++; notify(); }
export function getVersion() { return `${stateDirty}:${progressByAppid.size}`; }
export function subscribe(fn: Listener) { listeners.add(fn); return () => { listeners.delete(fn); }; }
function notify() { listeners.forEach(fn => fn()); }
```

`src/components/PostInstallModal.tsx`:

```tsx
import { ConfirmModal } from "@decky/ui";

export function PostInstallModal({ modId, loader, closeModal }: {
  modId: string; loader: string; closeModal?: () => void;
}) {
  return (
    <ConfirmModal strTitle="Fix installed — one more step"
      strOKButtonText="Got it" onOK={closeModal} onCancel={closeModal} bCancelDisabled>
      <div>
        <p>To activate <b>{modId}</b>, enable its launch option:</p>
        <ol>
          <li>Open the game's menu (the one with “Properties...”)</li>
          <li>Select <b>Launch Options</b></li>
          <li>Turn ON <b>{modId}</b> under “Lyall Fixes”</li>
        </ol>
        <p>A Launch Options import dialog may also appear — accept it.</p>
        {loader === "bepinex" && (
          <p>⚠️ First launch can take several minutes (BepInEx builds its cache) — don't force-quit.</p>
        )}
      </div>
    </ConfirmModal>
  );
}
```

`src/components/ManualLaunchOptionModal.tsx`:

```tsx
import { ConfirmModal } from "@decky/ui";
import { toaster } from "@decky/api";
import { manualLaunchOption } from "../lib/launchOptions";
import { setLaunchOptionHandled } from "../api";

export function ManualLaunchOptionModal({ modId, appid, dll, loader, closeModal }: {
  modId: string; appid: number; dll: string; loader: string; closeModal?: () => void;
}) {
  const line = manualLaunchOption(dll);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(line);
      toaster.toast({ title: "Copied", body: "Paste into Properties → Launch Options" });
    } catch {
      toaster.toast({ title: "Copy failed", body: "Add the line manually" });
    }
  };
  return (
    <ConfirmModal strTitle="Fix installed — add the launch option"
      strOKButtonText="Copy launch option"
      strCancelButtonText="I've added it"
      onOK={() => { void copy(); }}
      onCancel={() => { void setLaunchOptionHandled(modId, appid, "manual_confirmed"); closeModal?.(); }}>
      <div>
        <p>Without the Launch Options plugin, add this line to the game's
          <b> Properties → Launch Options</b> yourself:</p>
        <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{line}</pre>
        {loader === "bepinex" && (
          <p>⚠️ First launch can take several minutes (BepInEx builds its cache).</p>
        )}
      </div>
    </ConfirmModal>
  );
}
```

`src/components/GameRowItem.tsx`:

```tsx
import { ButtonItem, Field, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import type { GameRow } from "../api";
import { installMod, uninstallMod } from "../api";
import { dispatchDlo, hasDLO, manualLaunchOption } from "../lib/launchOptions";

function statusText(row: GameRow): string {
  if (row.busy) return `${row.busy.phase}… ${row.busy.pct != null ? `${row.busy.pct}%` : ""}`;
  switch (row.status) {
    case "installed": {
      const warn = row.override_status === "not_registered" || row.override_status === "registered_disabled";
      return warn ? `Installed ${row.installed_version} — launch override not enabled`
                  : `Installed ${row.installed_version}`;
    }
    case "update_available": return `Installed ${row.installed_version} · ${row.latest_version} available`;
    case "needs_launch_option": return `Installed ${row.installed_version} — add launch option`;
    case "needs_curation": return "Awaiting catalog data";
    case "not_installed": return row.blocked_by ? `Blocked: ${row.blocked_by} installed` : `${row.latest_version} available`;
    default: return "Unknown";
  }
}

export function GameRowItem({ row, onAction }: { row: GameRow; onAction: () => void }) {
  const installed = row.status === "installed" || row.status === "update_available"
    || row.status === "needs_launch_option";
  const overrideWarn = installed && hasDLO()
    && (row.override_status === "not_registered" || row.override_status === "registered_disabled");

  const run = async (fn: () => Promise<{ ok: boolean; message?: string }>) => {
    try {
      const res = await fn();
      if (!res.ok) toaster.toast({ title: row.mod_id, body: res.message ?? "Failed" });
    } catch {
      // Last-resort net for bridge bugs — backend callables normally never reject.
      toaster.toast({ title: row.mod_id, body: "Something went wrong — check the Decky log" });
    }
    onAction();
  };

  return (
    <>
      <PanelSectionRow>
        <Field label={`${row.name} — ${row.mod_id}`} description={statusText(row)} />
      </PanelSectionRow>
      {!row.busy && (row.status === "not_installed" && !row.blocked_by) && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => installMod(row.mod_id, row.appid))}>
            Install
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && row.status === "update_available" && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => installMod(row.mod_id, row.appid))}>
            Update to {row.latest_version}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && overrideWarn && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => {
            dispatchDlo(row.mod_id, row.wine_dll_override);
            toaster.toast({ title: row.mod_id, body: "Sent to Launch Options — accept the import dialog" });
          }}>
            Register launch option
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && row.status === "needs_launch_option" && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => {
            void navigator.clipboard?.writeText(manualLaunchOption(row.wine_dll_override));
            toaster.toast({ title: row.mod_id, body: "Launch option copied" });
          }}>
            Copy launch option
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && installed && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => uninstallMod(row.mod_id, row.appid))}>
            Uninstall
          </ButtonItem>
        </PanelSectionRow>
      )}
    </>
  );
}
```

`src/components/Panel.tsx`:

```tsx
import { useEffect, useState } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field } from "@decky/ui";
import { getState, refresh, type StateResult } from "../api";
import { sortRows } from "../lib/sort";
import { hasDLO } from "../lib/launchOptions";
import { subscribe, progressByAppid } from "../store";
import { GameRowItem } from "./GameRowItem";

function age(iso?: string | null): string {
  if (!iso) return "never";
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return mins < 60 ? `${mins}m ago` : `${Math.round(mins / 60)}h ago`;
}

export function Panel() {
  const [state, setState] = useState<StateResult | null>(null);
  const load = () => { void getState().then(setState); };

  useEffect(() => {
    load();
    return subscribe(load);
  }, []);

  const rows = (state?.games ?? []).map(r =>
    ({ ...r, busy: progressByAppid.get(r.appid) ?? r.busy }));

  return (
    <>
      {!hasDLO() && (
        <PanelSection title="Recommended">
          <PanelSectionRow>
            <Field description={'Install the "Launch Options" plugin from the Decky store for one-toggle activation. Without it you must paste launch options manually.'} />
          </PanelSectionRow>
        </PanelSection>
      )}
      <PanelSection title="Games">
        {state === null && <PanelSectionRow><Field description="Loading…" /></PanelSectionRow>}
        {state !== null && rows.length === 0 && (
          <PanelSectionRow><Field description="No installed games with available fixes." /></PanelSectionRow>
        )}
        {sortRows(rows).map(row => (
          <GameRowItem key={`${row.appid}-${row.mod_id}`} row={row} onAction={load} />
        ))}
      </PanelSection>
      <PanelSection title="Catalog">
        <PanelSectionRow>
          <Field label="Catalog updated" description={age(state?.catalog_updated_at)} />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => { void refresh().then(setState); }}>
            Refresh
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}
```

`src/index.tsx` (replace stub):

```tsx
import { definePlugin, addEventListener, removeEventListener, toaster } from "@decky/api";
import { showModal, staticClasses } from "@decky/ui";
import { FaScrewdriverWrench } from "react-icons/fa6";
import { Panel } from "./components/Panel";
import { PostInstallModal } from "./components/PostInstallModal";
import { ManualLaunchOptionModal } from "./components/ManualLaunchOptionModal";
import { dispatchDlo, hasDLO } from "./lib/launchOptions";
import { setLaunchOptionHandled } from "./api";
import { setProgress, markStateDirty } from "./store";

export default definePlugin(() => {
  // Module-scope listeners: completion handling must work with the QAM closed.
  const onProgress = addEventListener<[string, number, string, number | null]>(
    "qf_progress", (modId, appid, phase, pct) => {
      setProgress(appid, { op: "install", phase, pct });
    });

  const onDone = addEventListener<[string, string, number, boolean, string, string, string]>(
    "qf_done", (op, modId, appid, okFlag, code, dll, loader) => {
      setProgress(appid, null);
      markStateDirty();
      if (!okFlag) {
        toaster.toast({ title: modId, body: `Failed: ${code}` });
        return;
      }
      if (op === "install") {
        if (hasDLO()) {
          dispatchDlo(modId, dll);
          void setLaunchOptionHandled(modId, appid, "dlo");
          showModal(<PostInstallModal modId={modId} loader={loader} />);
        } else {
          showModal(<ManualLaunchOptionModal modId={modId} appid={appid} dll={dll} loader={loader} />);
        }
      } else {
        toaster.toast({
          title: modId,
          body: hasDLO()
            ? "Uninstalled — turn OFF its toggle in Launch Options"
            : "Uninstalled — remove its line from Launch Options",
        });
      }
    });

  return {
    name: "Lyall Fixes",
    titleView: <div className={staticClasses.Title}>Lyall Fixes</div>,
    content: <Panel />,
    icon: <FaScrewdriverWrench />,
    onDismount() {
      removeEventListener("qf_progress", onProgress);
      removeEventListener("qf_done", onDone);
    },
  };
});
```

- [ ] **Step 2: Build**

Run: `pnpm run build && pnpm run test`
Expected: `dist/index.js` builds clean; vitest still green.

- [ ] **Step 3: Commit** — `git add -A && git commit -m "feat: QAM panel, install flow UX, DLO and manual launch-option modals"`

---

### Task 12: CI, packaging, README

**Files:**
- Create: `.github/workflows/ci.yml`, `README.md`

- [ ] **Step 1: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-asyncio
      - run: python -m pytest -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm run test
      - run: pnpm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  release:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist
      - name: Package plugin zip
        run: |
          mkdir -p out/decky-lyall
          cp -r dist plugin.json package.json main.py py_modules LICENSE README.md out/decky-lyall/
          find out -name '__pycache__' -type d -exec rm -rf {} +
          cd out && zip -r decky-lyall.zip decky-lyall
      - uses: softprops/action-gh-release@v2
        with:
          files: out/decky-lyall.zip
```

- [ ] **Step 2: `README.md`**

```markdown
# Lyall Fixes (decky-lyall)

Decky Loader plugin that installs [Lyall's PC game fixes](https://codeberg.org/Lyall)
into your Steam games on SteamOS, from Gaming Mode.

Companion to [QuickFix](https://github.com/sharkusmanch/quickfix) (Windows CLI) —
both share the same auto-refreshed catalog.

## Install

1. Install [Decky Loader](https://decky.xyz).
2. Decky Settings → Developer → **Install Plugin from URL**:
   `https://github.com/sharkusmanch/decky-lyall/releases/latest/download/decky-lyall.zip`
3. Strongly recommended: install **Launch Options** (Wurielle) from the Decky store —
   Lyall's fixes need a `WINEDLLOVERRIDES` launch option under Proton, and this plugin
   registers a one-toggle option with it after each install. Without it, you get a
   copy-to-clipboard fallback.

## Usage

Open the Quick Access Menu → Lyall Fixes. Games you have installed that have an
available fix are listed; Install downloads the pinned, hash-verified release from
Codeberg and places files in the right directory. After installing, enable the fix's
toggle: game menu (with "Properties...") → Launch Options → turn ON the option under
"Lyall Fixes". BepInEx-based fixes take several minutes on first launch.

## Notes

- Uninstalling a fix restores any game files it replaced.
- Uninstalling this **plugin** does NOT remove installed fixes — uninstall fixes first.
- Game updates may break a fix until Lyall ships a new release; use Update when shown.
- Use at your own risk: fixes are third-party mods (MIT-licensed, source on Codeberg).
```

- [ ] **Step 3: Validate YAML + full local check**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && python3 -m pytest -q && pnpm run test && pnpm run build && echo ALL OK`
Expected: `ALL OK`.

- [ ] **Step 4: Commit and push**

```bash
git add -A && git commit -m "ci: test, build, and release packaging"
git push -u origin main
```

Expected: CI green on GitHub.

---

### Task 13: On-device smoke test (manual — requires a Steam Deck)

Cannot run from this pod; execute when a Deck is available. Sideload: build zip locally (`mkdir -p out/decky-lyall && cp -r dist plugin.json package.json main.py py_modules LICENSE README.md out/decky-lyall/ && cd out && zip -r decky-lyall.zip decky-lyall`), then `rsync out/decky-lyall deck@<ip>:~/homebrew/plugins/` and `ssh deck@<ip> sudo systemctl restart plugin_loader`.

- [ ] Panel lists installed games with fixes; names resolve; catalog age shown.
- [ ] Install a **pathed** mod (FF7RebirthFix): files land under `End/Binaries/Win64/`, sha256 verified, progress bar during download, `qf_done` toast/modal fires with QAM closed.
- [ ] Install a **flat+subdir** mod (ClairObscurFix): files land in `Sandfall/Binaries/Win64/` next to the shipping exe.
- [ ] Install a **BepInEx** mod (RaidouFix): slow-first-boot warning shows; game boots with fix active after enabling the toggle.
- [ ] DLO choreography: import dialog appears and is focusable with QAM open; decline it → row shows "launch override not enabled" and **Register launch option** recovers; enable toggle → warning clears on refresh. Verify our modal doesn't stack under DLO's.
- [ ] Verify instruction copy matches the DLO **store** build's menu labels; adjust wording if the store version differs.
- [ ] Without DLO installed: manual modal appears, clipboard works, "I've added it" clears the row warning; fix loads in-game with pasted option.
- [ ] Uninstall restores replaced files (`game.ini` byte-identical) and clears the row.
- [ ] Launch the game during an install attempt → `game_running` toast, nothing written.
- [ ] Tag `v0.1.0`, push, confirm the release zip installs via "Install from URL".
