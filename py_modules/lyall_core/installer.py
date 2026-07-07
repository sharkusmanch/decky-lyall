import hashlib
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass

from . import manifest
from .errors import OpError
from .extract import safe_extract


@dataclass
class Paths:
    runtime_dir: str

    def __post_init__(self):
        self.downloads = os.path.join(self.runtime_dir, "downloads")
        self.staging = os.path.join(self.runtime_dir, "staging")
        for d in (self.downloads, self.staging):
            os.makedirs(d, exist_ok=True)


def target_dir_for(mod, appid, install_path):
    game = next((g for g in mod.get("games", []) if g.get("steam_appid") == appid), None)
    if game is None:
        raise OpError("not_found")
    if mod["zip_layout"] == "pathed":
        return install_path
    # "." is the catalog's explicit "extract to install root" marker for flat zips;
    # absence means the target dir is unknown and the install is blocked.
    subdir = game.get("install_subdir")
    if not subdir:
        raise OpError("needs_curation")
    return os.path.normpath(os.path.join(install_path, subdir))


async def download_verified(open_stream, mod, dest, progress):
    """Stream the pinned asset to dest, verifying size and sha256 as bytes arrive."""
    h = hashlib.sha256()
    total = 0
    with open(dest, "wb") as f:
        async for chunk in open_stream(mod["download_url"]):
            total += len(chunk)
            if total > mod["size"]:
                break
            h.update(chunk)
            f.write(chunk)
            progress("download", int(total * 100 / mod["size"]))
    if total != mod["size"] or h.hexdigest() != mod["sha256"]:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise OpError("verify_failed")


async def install(*, mod_id, mod, appid, install_path, paths, open_stream, progress,
                  game_running, now):
    if game_running(install_path):
        raise OpError("game_running")
    target_dir = target_dir_for(mod, appid, install_path)
    os.makedirs(target_dir, exist_ok=True)

    zip_path = os.path.join(paths.downloads, f"{mod_id}-{mod['derived_release']}.zip")
    await download_verified(open_stream, mod, zip_path, progress)

    old = manifest.load(paths.runtime_dir, appid, mod_id)
    owned = set(old["files"]) if old else set()
    backup_dir = manifest.backup_dir_for(paths.runtime_dir, appid, mod_id)
    staging = tempfile.mkdtemp(dir=paths.staging)
    try:
        progress("extract", None)
        with zipfile.ZipFile(zip_path) as zf:
            written, newly_backed = safe_extract(zf, target_dir, staging,
                                                 owned_files=owned, backup_dir=backup_dir)
        if old:
            m, stale = manifest.apply_update(old, files=written,
                                             version=mod["derived_release"],
                                             sha256=mod["sha256"],
                                             newly_backed_up=newly_backed,
                                             installed_at=now())
            for rel in stale:
                try:
                    os.remove(os.path.join(old["target_dir"], rel))
                except OSError:
                    pass
        else:
            m = manifest.build(mod_id=mod_id, appid=appid, version=mod["derived_release"],
                               sha256=mod["sha256"], install_path=install_path,
                               target_dir=target_dir, files=written,
                               backed_up_files=newly_backed,
                               wine_dll_override=mod["wine_dll_override"],
                               launch_option_handled="manual_pending",
                               installed_at=now())
        manifest.save(paths.runtime_dir, m)
        return m
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            os.remove(zip_path)
        except OSError:
            pass


def uninstall(paths, *, appid, mod_id):
    m = manifest.load(paths.runtime_dir, appid, mod_id)
    if m is None:
        raise OpError("not_found")
    for rel in m["files"]:
        try:
            os.remove(os.path.join(m["target_dir"], rel))
        except OSError:
            pass
    backup_dir = manifest.backup_dir_for(paths.runtime_dir, appid, mod_id)
    for rel in m["backed_up_files"]:
        src = os.path.join(backup_dir, rel)
        dst = os.path.join(m["target_dir"], rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst) or m["target_dir"], exist_ok=True)
            shutil.copy2(src, dst)
    manifest.remove(paths.runtime_dir, appid, mod_id)
    return m
