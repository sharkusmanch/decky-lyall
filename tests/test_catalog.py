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
