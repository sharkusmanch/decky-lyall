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
