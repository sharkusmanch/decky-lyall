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
