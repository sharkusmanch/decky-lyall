import json
import os
import shutil

SCHEMA = 1


def _installs_dir(runtime_dir):
    return os.path.join(runtime_dir, "installs")


def path_for(runtime_dir, appid, mod_id):
    return os.path.join(_installs_dir(runtime_dir), f"{appid}-{mod_id}.json")


def backup_dir_for(runtime_dir, appid, mod_id):
    return os.path.join(runtime_dir, "backups", f"{appid}-{mod_id}")


def build(*, mod_id, appid, version, sha256, install_path, target_dir, files,
          backed_up_files, wine_dll_override, launch_option_handled, installed_at):
    return {
        "schema": SCHEMA, "mod_id": mod_id, "appid": appid, "version": version,
        "sha256": sha256, "install_path": install_path, "target_dir": target_dir,
        "files": list(files), "backed_up_files": list(backed_up_files),
        "wine_dll_override": wine_dll_override,
        "launch_option_handled": launch_option_handled, "installed_at": installed_at,
    }


def apply_update(old, *, files, version, sha256, newly_backed_up, installed_at):
    """New manifest for an update: carries pristine backups forward; returns files
    from the old release that the new one no longer ships (caller deletes them)."""
    stale = [f for f in old["files"] if f not in set(files)]
    new = dict(old)
    new.update(version=version, sha256=sha256, files=list(files), installed_at=installed_at,
               backed_up_files=sorted(set(old["backed_up_files"]) | set(newly_backed_up)))
    return new, stale


def save(runtime_dir, m):
    os.makedirs(_installs_dir(runtime_dir), exist_ok=True)
    with open(path_for(runtime_dir, m["appid"], m["mod_id"]), "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2)


def load(runtime_dir, appid, mod_id):
    try:
        with open(path_for(runtime_dir, appid, mod_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_all(runtime_dir):
    out = []
    d = _installs_dir(runtime_dir)
    if not os.path.isdir(d):
        return out
    for entry in sorted(os.listdir(d)):
        if entry.endswith(".json"):
            try:
                with open(os.path.join(d, entry), encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, ValueError):
                continue
    return out


def remove(runtime_dir, appid, mod_id):
    try:
        os.remove(path_for(runtime_dir, appid, mod_id))
    except OSError:
        pass
    shutil.rmtree(backup_dir_for(runtime_dir, appid, mod_id), ignore_errors=True)


def prune_orphans(runtime_dir):
    """Drop manifests whose game install dir is gone (game uninstalled — Steam removed
    the whole dir, so restoration is meaningless). Returns [(appid, mod_id)] removed."""
    removed = []
    for m in load_all(runtime_dir):
        if not os.path.isdir(m["install_path"]):
            remove(runtime_dir, m["appid"], m["mod_id"])
            removed.append((m["appid"], m["mod_id"]))
    return removed
