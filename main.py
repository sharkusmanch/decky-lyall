import asyncio
import json
import os
import ssl
from datetime import datetime, timezone

import aiohttp
import certifi

import decky
from lyall_core import catalog, configs, dlo, installer, manifest, ops as ops_mod, procs, state
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
        self.mods = {}
        self.catalog_updated_at = None
        self._steam_root = None
        raw, fetched_at = catalog.load_cache(self.settings_dir)
        if raw:
            self._adopt_catalog(raw, fetched_at)
        self.loop.create_task(self._fetch_catalog())
        decky.logger.info("Lyall Fixes loaded")

    def _adopt_catalog(self, raw, fetched_at):
        usable, skipped = catalog.usable_mods(raw)
        self.mods = usable
        self.catalog_updated_at = fetched_at
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
        if self._steam_root is None:
            self._steam_root = steam_mod.find_steam_root(decky.DECKY_USER_HOME)
        return steam_mod.installed_games(self._steam_root) if self._steam_root else {}

    def _state(self):
        rows = state.build_rows(
            mods=self.mods, installed=self._installed_games(),
            manifests=manifest.load_all(self.paths.runtime_dir),
            dlo_text=dlo.read_settings_text(decky.DECKY_USER_HOME),
            busy_map=self.ops.busy_map())
        return ok(catalog_updated_at=self.catalog_updated_at, games=rows)

    async def get_state(self):
        try:
            return self._state()
        except Exception:
            decky.logger.exception("get_state failed")
            return fail("unexpected")

    async def refresh(self):
        try:
            fetched = await self._fetch_catalog()
            manifest.prune_orphans(self.paths.runtime_dir)
            result = self._state()
            if not fetched:
                result.update(code="network_offline",
                              message="No connection — using cached data")
            return result
        except Exception:
            decky.logger.exception("refresh failed")
            return fail("unexpected")

    async def install(self, mod_id, appid):
        return self._start_op("install", mod_id, appid)

    async def uninstall(self, mod_id, appid):
        return self._start_op("uninstall", mod_id, appid)

    def _config_context(self, mod_id, appid, relpath=None):
        """Common guards for config callables: installed mod + declared file name."""
        m = manifest.load(self.paths.runtime_dir, appid, mod_id)
        mod = self.mods.get(mod_id)
        if m is None or mod is None:
            raise OpError("not_found")
        declared = {os.path.basename(n).lower() for n in mod.get("config_files", [])}
        if relpath is not None and os.path.basename(relpath).lower() not in declared:
            raise OpError("not_found", "not a declared config file")
        return m, mod

    async def list_configs(self, mod_id, appid):
        try:
            m, mod = self._config_context(mod_id, appid)
            found = configs.find_config_files(m["install_path"], mod.get("config_files", []))
            return ok(configs=found, loader=mod.get("loader", "ual"))
        except OpError as e:
            return fail(e.code, e.message)
        except Exception:
            decky.logger.exception("list_configs failed")
            return fail("unexpected")

    async def read_config(self, mod_id, appid, relpath):
        try:
            m, _ = self._config_context(mod_id, appid, relpath)
            return ok(entries=configs.read_entries(m["install_path"], relpath))
        except OpError as e:
            return fail(e.code, e.message)
        except Exception:
            decky.logger.exception("read_config failed")
            return fail("unexpected")

    async def set_config_value(self, mod_id, appid, relpath, section, key, value):
        try:
            m, _ = self._config_context(mod_id, appid, relpath)
            configs.write_value(m["install_path"], relpath, section, key, value)
            return ok()
        except OpError as e:
            return fail(e.code, e.message)
        except Exception:
            decky.logger.exception("set_config_value failed")
            return fail("unexpected")

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
            if op == "install":
                mod = self.mods.get(mod_id)
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
        entry = self.ops.get(appid)
        mod_id = entry["mod_id"] if entry else ""
        self.loop.create_task(decky.emit("qf_progress", mod_id, appid, phase, pct))

    async def _unload(self):
        decky.logger.info("Lyall Fixes unloading")

    async def _uninstall(self):
        # Installed fixes, manifests, and DLO options stay — removing mods from game
        # dirs on plugin uninstall would be surprising and unrecoverable (documented in README).
        decky.logger.info("Lyall Fixes uninstalled; installed fixes left in place")
