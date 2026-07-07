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

## Development

- Backend logic lives in `py_modules/lyall_core/` (pure Python, `pytest` suite).
- Frontend: `pnpm install && pnpm run build` (rollup via `@decky/rollup`), `pnpm run test` (vitest).
- Deploy to a Deck: build, then rsync the packaged folder to `~/homebrew/plugins/` and
  `sudo systemctl restart plugin_loader`.
