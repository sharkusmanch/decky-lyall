from lyall_core import detect


def test_detects_engine_dir_over_root_stub(tmp_path):
    (tmp_path / "runtime/media").mkdir(parents=True)
    (tmp_path / "runtime/media/LostJudgment.exe").write_bytes(b"x" * 1000)
    (tmp_path / "runtime/media/startup.exe").write_bytes(b"x" * 10)   # stub
    (tmp_path / "crashpad_handler.exe").write_bytes(b"x" * 50)         # stub at root
    c = detect.detect_install_subdir(str(tmp_path))
    assert c[0] == {"subdir": "runtime/media", "exe": "runtime/media/LostJudgment.exe"}


def test_largest_nonstub_exe_when_no_engine_dir(tmp_path):
    (tmp_path / "Game.exe").write_bytes(b"x" * 5000)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/editor.exe").write_bytes(b"x" * 100)
    c = detect.detect_install_subdir(str(tmp_path))
    assert c[0]["subdir"] == "." and c[0]["exe"] == "Game.exe"


def test_ue_binaries_win64(tmp_path):
    d = tmp_path / "Game/Binaries/Win64"
    d.mkdir(parents=True)
    (d / "Game-Win64-Shipping.exe").write_bytes(b"x" * 2000)
    c = detect.detect_install_subdir(str(tmp_path))
    assert c[0]["subdir"] == "Game/Binaries/Win64"


def test_stubs_only_returns_empty(tmp_path):
    (tmp_path / "UnityCrashHandler64.exe").write_bytes(b"x")
    (tmp_path / "unins000.exe").write_bytes(b"x")
    assert detect.detect_install_subdir(str(tmp_path)) == []


def test_skips_symlinked_dirs(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "Game.exe").write_bytes(b"x" * 100)
    (tmp_path / "link").symlink_to(real)
    subs = [x["subdir"] for x in detect.detect_install_subdir(str(tmp_path))]
    assert "real" in subs and "link" not in subs
