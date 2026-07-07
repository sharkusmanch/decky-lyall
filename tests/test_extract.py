import io
import zipfile

import pytest

from lyall_core import extract
from lyall_core.errors import OpError


def _zf(entries):
    """entries: {name: bytes} or a list of (ZipInfo, bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if isinstance(entries, dict):
            for name, data in entries.items():
                z.writestr(name, data)
        else:
            for info, data in entries:
                z.writestr(info, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def _run(zf, target, staging, owned=frozenset(), backups=None):
    return extract.safe_extract(zf, str(target), str(staging),
                                owned_files=owned, backup_dir=str(backups or target / ".bk"))


def test_basic_extraction(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    written, backed = _run(_zf({"Fix.asi": b"a", "dsound.dll": b"d"}), t, s)
    assert (t / "Fix.asi").read_bytes() == b"a"
    assert sorted(written) == ["Fix.asi", "dsound.dll"] and backed == []


def test_backslash_entries_become_dirs(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    _run(_zf({"End\\Binaries\\Win64\\dsound.dll": b"d"}), t, s)
    assert (t / "End/Binaries/Win64/dsound.dll").exists()


def test_marker_file_skipped(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    written, _ = _run(_zf({"EXTRACT_TO_GAME_FOLDER": b"", "Fix.asi": b"a"}), t, s)
    assert written == ["Fix.asi"]


@pytest.mark.parametrize("name", ["../evil.dll", "a/../../evil.dll", "/etc/evil", "C:/evil.dll"])
def test_unsafe_paths_rejected(tmp_path, name):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    with pytest.raises(OpError):
        _run(_zf({name: b"x"}), t, s)
    assert not (tmp_path / "evil.dll").exists()


def test_symlink_entries_skipped(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    info = zipfile.ZipInfo("link")
    info.external_attr = 0o120777 << 16  # S_IFLNK
    written, _ = _run(_zf([(info, b"/etc/passwd"), (zipfile.ZipInfo("Fix.asi"), b"a")]), t, s)
    assert written == ["Fix.asi"] and not (t / "link").exists()


def test_case_insensitive_merge(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    (t / "End/Binaries/Win64").mkdir(parents=True); s.mkdir()
    _run(_zf({"end/binaries/win64/dsound.dll": b"d"}), t, s)
    assert (t / "End/Binaries/Win64/dsound.dll").exists()
    assert not (t / "end").exists()


def test_pristine_backup_only_for_unowned_files(tmp_path):
    t, s, bk = tmp_path / "game", tmp_path / "staging", tmp_path / "bk"
    t.mkdir(); s.mkdir()
    (t / "game.ini").write_bytes(b"original")   # pristine game file
    (t / "Fix.asi").write_bytes(b"old-mod")     # our own previous version
    written, backed = _run(_zf({"game.ini": b"modded", "Fix.asi": b"new-mod"}), t, s,
                           owned={"Fix.asi"}, backups=bk)
    assert backed == ["game.ini"]
    assert (bk / "game.ini").read_bytes() == b"original"
    assert not (bk / "Fix.asi").exists()


def test_backups_are_write_once(tmp_path):
    t, s, bk = tmp_path / "game", tmp_path / "staging", tmp_path / "bk"
    t.mkdir(); s.mkdir(); bk.mkdir()
    (bk / "game.ini").write_bytes(b"original")
    (t / "game.ini").write_bytes(b"already-modded")
    _run(_zf({"game.ini": b"modded-again"}), t, s, backups=bk)
    assert (bk / "game.ini").read_bytes() == b"original"


def test_rollback_on_failure(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    (t / "exists.txt").write_bytes(b"original")
    zf = _zf({"exists.txt": b"overwritten", "ok.txt": b"new", "../evil": b"x"})
    with pytest.raises(OpError):
        _run(zf, t, s)
    assert (t / "exists.txt").read_bytes() == b"original"
    assert not (t / "ok.txt").exists()


def test_entry_count_cap(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    saved = extract.MAX_ENTRIES
    extract.MAX_ENTRIES = 3
    try:
        with pytest.raises(OpError):
            _run(_zf({f"f{i}": b"x" for i in range(4)}), t, s)
    finally:
        extract.MAX_ENTRIES = saved


def test_lying_size_header_rejected(tmp_path):
    t, s = tmp_path / "game", tmp_path / "staging"
    t.mkdir(); s.mkdir()
    info = zipfile.ZipInfo("liar.bin")
    zf = _zf([(info, b"A" * 1000)])
    zf.getinfo("liar.bin").file_size = 10  # declared < actual
    with pytest.raises(OpError):
        _run(zf, t, s)
