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
