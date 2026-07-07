import hashlib
import io
import zipfile

import pytest

from lyall_core import installer, manifest
from lyall_core.errors import OpError


def _zip_blob(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def _mod(blob, layout="flat", subdir="Bin", tag="0.0.1"):
    return {
        "games": [{"steam_appid": 42, **({"install_subdir": subdir} if subdir else {})}],
        "wine_dll_override": "dsound", "loader": "ual", "zip_layout": layout,
        "derived_release": tag,
        "download_url": "https://codeberg.org/x/F.zip",
        "sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob),
    }


def _stream(blob):
    async def stream(url):
        yield blob[: len(blob) // 2]
        yield blob[len(blob) // 2:]
    return stream


async def _install(tmp_path, blob, mod, game_running=lambda p: False):
    game = tmp_path / "game"
    game.mkdir(exist_ok=True)
    paths = installer.Paths(runtime_dir=str(tmp_path / "runtime"))
    m = await installer.install(
        mod_id="FooFix", mod=mod, appid=42, install_path=str(game), paths=paths,
        open_stream=_stream(blob), progress=lambda phase, pct: None,
        game_running=game_running, now=lambda: "t0")
    return m, game


async def test_install_flat_with_subdir(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a", "dsound.dll": b"d"})
    m, game = await _install(tmp_path, blob, _mod(blob))
    assert (game / "Bin/dsound.dll").exists()
    assert m["version"] == "0.0.1" and m["target_dir"].endswith("/Bin")
    assert sorted(m["files"]) == ["Fix.asi", "dsound.dll"]


async def test_install_pathed_to_root(tmp_path):
    blob = _zip_blob({"End/Binaries/Win64/dsound.dll": b"d"})
    m, game = await _install(tmp_path, blob, _mod(blob, layout="pathed", subdir=None))
    assert (game / "End/Binaries/Win64/dsound.dll").exists()


async def test_flat_without_subdir_blocked(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, _mod(blob, subdir=None))
    assert e.value.code == "needs_curation"


async def test_bad_hash_rejected(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    mod = _mod(blob)
    mod["sha256"] = "f" * 64
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, mod)
    assert e.value.code == "verify_failed"


async def test_game_running_blocks_before_download(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a"})
    with pytest.raises(OpError) as e:
        await _install(tmp_path, blob, _mod(blob), game_running=lambda p: True)
    assert e.value.code == "game_running"


async def test_update_deletes_stale_and_uninstall_restores(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "Bin").mkdir()
    (game / "Bin/game.ini").write_bytes(b"original")  # pristine, will be overwritten

    v1 = _zip_blob({"Fix.asi": b"1", "gone.dll": b"1", "game.ini": b"mod1"})
    paths = installer.Paths(runtime_dir=str(tmp_path / "runtime"))

    async def run(blob, mod):
        return await installer.install(mod_id="FooFix", mod=mod, appid=42,
                                       install_path=str(game), paths=paths,
                                       open_stream=_stream(blob),
                                       progress=lambda *a: None,
                                       game_running=lambda p: False, now=lambda: "t")

    await run(v1, _mod(v1))
    v2 = _zip_blob({"Fix.asi": b"2", "game.ini": b"mod2"})
    m2 = await run(v2, _mod(v2, tag="0.0.2"))
    assert not (game / "Bin/gone.dll").exists()          # stale file removed
    assert m2["backed_up_files"] == ["game.ini"]          # pristine backup carried

    installer.uninstall(paths, appid=42, mod_id="FooFix")
    assert not (game / "Bin/Fix.asi").exists()
    assert (game / "Bin/game.ini").read_bytes() == b"original"
    assert manifest.load(paths.runtime_dir, 42, "FooFix") is None


async def test_install_flat_root_confirmed_dot_subdir(tmp_path):
    blob = _zip_blob({"Fix.asi": b"a", "dsound.dll": b"d"})
    m, game = await _install(tmp_path, blob, _mod(blob, subdir="."))
    assert (game / "dsound.dll").exists()          # extracted at install root
    assert m["target_dir"] == str(game)            # normalized, no trailing '/.'
