from lyall_core import configs


def test_find_config_files_by_basename(tmp_path):
    game = tmp_path / "game"
    (game / "Bin").mkdir(parents=True)
    (game / "Bin/FooFix.ini").write_text("[A]\nx = 1\n")
    found = configs.find_config_files(str(game), ["FooFix.ini"])
    assert found == [{"name": "FooFix.ini", "relpath": "Bin/FooFix.ini"}]


def test_find_config_files_bepinex_path_form(tmp_path):
    game = tmp_path / "game"
    (game / "BepInEx/config").mkdir(parents=True)
    (game / "BepInEx/config/RaidouFix.cfg").write_text("[General]\nEnabled = true\n")
    found = configs.find_config_files(str(game), ["RaidouFix.cfg"])
    assert found == [{"name": "RaidouFix.cfg", "relpath": "BepInEx/config/RaidouFix.cfg"}]


def test_find_config_files_missing_returns_empty(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    assert configs.find_config_files(str(game), ["FooFix.ini"]) == []


def test_read_entries_and_write_value_roundtrip(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    ini = game / "FooFix.ini"
    ini.write_text("[Fix]\nEnabled = true\nWidth = 1280\n")
    entries = configs.read_entries(str(game), "FooFix.ini")
    assert entries[0]["value"] == "true" and entries[0]["type"] == "bool"
    configs.write_value(str(game), "FooFix.ini", "Fix", "Width", "1920")
    assert "Width = 1920" in ini.read_text()


def test_relpath_escape_rejected(tmp_path):
    import pytest
    from lyall_core.errors import OpError
    game = tmp_path / "game"
    game.mkdir()
    (tmp_path / "outside.ini").write_text("[A]\nx = 1\n")
    with pytest.raises(OpError):
        configs.read_entries(str(game), "../outside.ini")


def test_oversized_config_rejected(tmp_path):
    import pytest
    from lyall_core.errors import OpError
    game = tmp_path / "game"
    game.mkdir()
    (game / "big.ini").write_text("[A]\n" + "x = 1\n" * 100000)
    saved = configs.MAX_CONFIG_BYTES
    configs.MAX_CONFIG_BYTES = 100
    try:
        with pytest.raises(OpError):
            configs.read_entries(str(game), "big.ini")
    finally:
        configs.MAX_CONFIG_BYTES = saved
