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


def test_row_needs_launch_option():
    man = {"schema": 1, "mod_id": "FooFix", "appid": 42, "version": "0.0.2",
           "files": [], "backed_up_files": [], "install_path": "/g", "target_dir": "/g/Bin",
           "sha256": "0" * 64, "wine_dll_override": "dsound",
           "launch_option_handled": "manual_pending", "installed_at": "t"}
    rows = _rows(manifests=[man])
    assert rows[0]["status"] == "needs_launch_option"
