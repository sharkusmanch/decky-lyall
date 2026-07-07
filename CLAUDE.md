# decky-lyall — Lyall Fixes

A Decky Loader plugin ("Lyall Fixes") that installs [Lyall's PC game fixes](https://codeberg.org/Lyall) into Steam games on SteamOS / Steam Deck, from Gaming Mode. Companion to the [QuickFix](https://github.com/sharkusmanch/quickfix) Windows CLI — both read the same catalog.

For general Decky Loader knowledge (the frontend/backend split, `@decky/api`/`@decky/ui`, SteamClient APIs, the frozen Python runtime, launch-option handling), the `developing-decky-plugins` skill is the reference. This file covers what's specific to *this* plugin.

## What it does

Lyall's fixes are ASI/BepInEx/MelonLoader mods activated by a proxy DLL (`dsound`, `winmm`, `dinput8`, `version`, `winhttp`) placed next to the game exe. Under Proton the DLL is inert unless the game also gets a `WINEDLLOVERRIDES="<dll>=n,b" %command%` launch option. So installing a fix means **both** placing files in the right directory **and** getting that launch option set. This plugin does the file install; launch options are delegated to the "Launch Options" plugin (DLO) or a manual copy fallback.

## Architecture

Standard Decky split, with **all logic in a pure, unit-tested backend package and a thin glue layer**:

- `py_modules/lyall_core/` — pure Python, imports nothing Decky-specific (paths and an emit callback are injected). This is where the real work lives and where the pytest suite runs offline.
- `main.py` — the `class Plugin` glue. Wires `lyall_core` to the `decky` module (settings/runtime dirs, `decky.emit`, logging), owns the async operation lifecycle, and exposes callables. **Untested** (imports `decky`, which only exists in the loader).
- `src/` — React frontend. Pure helpers in `src/lib/` are vitest-tested; components are verified on-device.

### Backend modules (`py_modules/lyall_core/`)

| Module | Responsibility |
|---|---|
| `catalog.py` | Fetch/validate/cache the remote `mods.json`. `usable_mods()` filters to entries safe to act on (defense-in-depth on remote input). |
| `steam.py` | Find the Steam root, parse `libraryfolders.vdf` + `appmanifest_*.acf`, enumerate installed games → install dirs. |
| `installer.py` | The core install/update/uninstall: pinned+hash-verified download, target-dir resolution, extraction, manifest write, stale-file cleanup, restore. |
| `extract.py` | Hardened zip extractor (backslash normalize, zip-slip guard, symlink skip, ext4 case-insensitive merge, bomb caps, staging rollback, pristine backups). |
| `manifest.py` | Per-install records under `installs/<appid>-<mod_id>.json`; update carry-forward, orphan pruning. |
| `detect.py` | Rank candidate install subdirs by locating the shipping exe (for uncurated flat mods). Proposes; never auto-applies. |
| `overrides.py` | Local `curation_overrides.json` — user-confirmed install paths layered over the catalog. |
| `configs.py` / `iniconfig.py` | Find and line-preserving-edit a fix's INI/cfg config file. |
| `dlo.py` | Read DLO's `~/.dlo/settings.json` to report per-fix override status (best-effort; degrades to `unknown`). |
| `state.py` | `build_rows()` — the single source of the UI row model (status precedence, override status, blocked-by, busy). |
| `ops.py` | In-memory one-operation-per-appid table + `run_operation` (always emits terminal `qf_done`, frees the slot). |
| `procs.py` | Running-game guard (scan `/proc` cmdlines for the install path). |
| `errors.py` | `OpError`, `fail(code, msg)`, `ok(**)` — the structured envelope every callable returns. |

## Key data contracts

**Catalog** (`mods.json`, produced by the quickfix repo, read-only here). Per-mod: `repo`, `config_files[]`, `games[{steam_appid, install_subdir?}]`, `wine_dll_override`, `loader` (`ual|bepinex|melonloader`), `zip_layout` (`flat|pathed`), `derived_release`, `download_url`, `sha256`, `size`. `catalog.usable_mods()` skips anything missing/invalid.

**`install_subdir` semantics** (per game entry):
- `zip_layout: pathed` → extract to install root (zip carries paths).
- `flat` + `install_subdir` set → extract there. `"."` is the explicit "root is correct" marker.
- `flat` + no `install_subdir` → **blocked** as `needs_curation` (never guess — a wrong dir installs a silently-inert fix). The "Detect fix location" flow resolves it on-device.

**Install manifest**: `{schema, mod_id, appid, version, sha256, install_path, target_dir, files[], backed_up_files[], wine_dll_override, launch_option_handled, installed_at}`. `launch_option_handled` ∈ `dlo | manual_pending | manual_confirmed`.

**Row status** (`state.build_rows`): `not_installed | installed | update_available | needs_curation | needs_launch_option | unknown`; plus `override_status` ∈ `registered_enabled | registered_disabled | not_registered | unknown`, `busy`, `blocked_by`.

**Callables** (frontend → backend): `get_state`, `refresh`, `install`, `uninstall`, `set_launch_option_handled`, `list_configs`, `read_config`, `set_config_value`, `detect_subdir`, `set_subdir_override`. All return `{ok, ...}` or `{ok: false, code, message}` — never raise across the bridge.

**Events** (backend → frontend, via `decky.emit`): `qf_progress(mod_id, appid, phase, pct)` and terminal `qf_done(op, mod_id, appid, ok, code, dll, loader)`. Progress emits are **awaited in order** before `qf_done` (a fire-and-forget late progress event would otherwise re-stick the UI on "extract" — see commit `da03cff`).

**DLO integration**: after install, the frontend dispatches `window.dispatchEvent(new CustomEvent('dlo-add-launch-options', {detail:[{id: 'lyall-<modId>', group: 'Lyall Fixes', on: 'WINEDLLOVERRIDES="<dll>=n,b"', off: '', enableGlobally: false}]}))` when `window.hasDeckyLaunchOptions`. Without DLO, a copy-to-clipboard modal is the fallback.

**On-disk layout** (backend): `DECKY_PLUGIN_RUNTIME_DIR/{downloads,staging,installs,backups}`, `DECKY_PLUGIN_SETTINGS_DIR/{catalog.json,curation_overrides.json}`.

## Commands

```bash
# Backend tests (offline, no Deck needed) — needs pytest + pytest-asyncio, Python 3.11
python -m pytest -q                 # 72 tests

# Frontend
pnpm install
pnpm run test                       # vitest (pure lib helpers)
pnpm run build                      # → dist/index.js

# Deploy to a Deck (plugins dir is root-owned → stage then sudo)
scp -r . deck@<ip>:/tmp/decky-lyall
ssh deck@<ip> "sudo rm -rf ~/homebrew/plugins/decky-lyall && \
  sudo cp -r /tmp/decky-lyall ~/homebrew/plugins/ && \
  sudo systemctl restart plugin_loader"
```

## Conventions

- **TDD, always.** Every `lyall_core` change is test-first. `main.py` and React components are the only untested code — keep them thin; if logic creeps in, push it into a `lyall_core` module and test it there.
- **Structured errors only.** Callables catch everything and return `{ok:false, code, message}` with a short toast-sized message; detail goes to `decky.logger`. Never let an exception cross the bridge.
- **Never guess an install path.** Blocked (`needs_curation`) beats a wrong guess. Detection proposes; the user confirms.
- **One operation per appid**, registered in `ops` before work starts; completion is delivered via `qf_done`, not by the frontend awaiting the call (so it survives the QAM closing).
- **Catalog is untrusted input** — validate in `catalog.usable_mods` even though the quickfix CI also validates.
- Frontend `hasDeckyLaunchOptions` is read live on every render (DLO may load after this plugin).

## Distribution

Off-store (the Decky store rejects majority-LLM-generated plugins): GitHub release zip → Decky Settings → Developer → Install from URL. `.github/workflows/ci.yml` runs pytest + vitest + build, and packages a release zip on `v*` tags. No compiled backend, no root flag → simplest runtime.

## Non-obvious gotchas (learned on-device)

- **Verify launch-option activation, don't assume.** A fix whose DLO toggle is off loads nothing while the panel would say "Installed" — `state.py` surfaces `override_status` so the row can warn.
- **Config files for BepInEx/MelonLoader fixes don't exist until first launch** (they're generated). `ConfigModal` shows a "run the game once" hint.
- **DragonTweak is multi-game with mixed layouts**: newer Dragon Engine titles extract to `runtime/media`, older ports (Yakuza 6, Kiwami 2) to the install root. This is why paths are verified per-appid, not pattern-matched.
- **`Router.MainRunningApp.appid` is a string** — `Number()`-coerce before comparing to numeric appids.
