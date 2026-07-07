from lyall_core import overrides


def test_set_load_roundtrip(tmp_path):
    overrides.set_subdir(str(tmp_path), 42, "FooFix", "runtime/media")
    assert overrides.load(str(tmp_path)) == {"42": {"FooFix": "runtime/media"}}


def test_load_missing_returns_empty(tmp_path):
    assert overrides.load(str(tmp_path)) == {}


def test_apply_layers_onto_catalog():
    mods = {"FooFix": {"games": [{"steam_appid": 42}, {"steam_appid": 43}]}}
    out = overrides.apply(mods, {"42": {"FooFix": "runtime/media"}})
    assert out["FooFix"]["games"][0]["install_subdir"] == "runtime/media"
    assert "install_subdir" not in out["FooFix"]["games"][1]
    assert "install_subdir" not in mods["FooFix"]["games"][0]  # original untouched


def test_apply_skips_unsafe_subdir():
    mods = {"F": {"games": [{"steam_appid": 1}]}}
    out = overrides.apply(mods, {"1": {"F": "../../etc"}})
    assert "install_subdir" not in out["F"]["games"][0]


def test_safe_subdir():
    assert overrides.safe_subdir("runtime/media")
    assert overrides.safe_subdir(".")
    assert not overrides.safe_subdir("../x")
    assert not overrides.safe_subdir("/abs")
    assert not overrides.safe_subdir("a/../../b")
