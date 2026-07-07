import os
import re
import shutil
import stat

from .errors import OpError

MAX_ENTRIES = 10_000
MAX_TOTAL_BYTES = 4 * 1024 ** 3
CHUNK = 65536
MARKER = "EXTRACT_TO_GAME_FOLDER"

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _normalize(name):
    return name.replace("\\", "/")


def _is_unsafe(name):
    return (name.startswith("/") or _DRIVE_RE.match(name) is not None
            or any(seg == ".." for seg in name.split("/")))


def _is_symlink(info):
    return stat.S_ISLNK(info.external_attr >> 16)


def _resolve_case(root, relpath):
    """Map relpath onto the existing tree case-insensitively (ext4 is case-sensitive;
    a case-mismatched duplicate tree means the DLL never loads)."""
    cur = root
    for part in [p for p in relpath.split("/") if p]:
        if os.path.isdir(cur):
            entries = os.listdir(cur)
            if part in entries:
                chosen = part
            else:
                matches = [e for e in entries if e.lower() == part.lower()]
                if len(matches) > 1:
                    raise OpError("extract_failed", f"ambiguous case variants for {part!r}")
                chosen = matches[0] if matches else part
            cur = os.path.join(cur, chosen)
        else:
            if os.path.isfile(cur):
                raise OpError("extract_failed", f"file blocks directory path: {cur}")
            cur = os.path.join(cur, part)
    return cur


def safe_extract(zf, target_dir, staging_dir, owned_files=frozenset(), backup_dir=None):
    """Extract zf into target_dir with zip-slip/symlink/bomb guards.

    owned_files: relpaths the current install manifest owns (never pristine-backed-up).
    backup_dir: write-once pristine backups of overwritten non-owned files.
    Returns (written_relpaths, newly_backed_up_relpaths). Rolls back on failure.
    """
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise OpError("extract_failed", "archive has too many entries")
    if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise OpError("extract_failed", "archive too large")

    real_target = os.path.realpath(target_dir)
    written = []          # (relpath, dest, staged_copy_or_None)
    newly_backed = []
    total_written = 0
    try:
        for info in infos:
            name = _normalize(info.filename)
            if not name or name.endswith("/"):
                continue
            if os.path.basename(name) == MARKER:
                continue
            if _is_unsafe(name):
                raise OpError("extract_failed", f"unsafe path in archive: {name!r}")
            if _is_symlink(info):
                continue

            dest = _resolve_case(real_target, name)
            real_dest = os.path.realpath(dest)
            if os.path.commonpath([real_target, real_dest]) != real_target:
                raise OpError("extract_failed", f"path escapes game dir: {name!r}")
            rel = os.path.relpath(real_dest, real_target)

            os.makedirs(os.path.dirname(dest) or dest, exist_ok=True)
            staged = None
            if os.path.exists(dest):
                staged = os.path.join(staging_dir, rel)
                os.makedirs(os.path.dirname(staged) or staging_dir, exist_ok=True)
                shutil.copy2(dest, staged)
                if backup_dir is not None and rel not in owned_files:
                    bpath = os.path.join(backup_dir, rel)
                    if not os.path.exists(bpath):
                        os.makedirs(os.path.dirname(bpath) or backup_dir, exist_ok=True)
                        shutil.copy2(dest, bpath)
                        newly_backed.append(rel)

            with zf.open(info) as src, open(dest, "wb") as out:
                while True:
                    chunk = src.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    total_written += len(chunk)
                    if out.tell() > info.file_size:
                        raise OpError("extract_failed", f"size header mismatch: {name!r}")
                    if total_written > MAX_TOTAL_BYTES:
                        raise OpError("extract_failed", "archive too large")
            written.append((rel, dest, staged))
        return [w[0] for w in written], newly_backed
    except Exception as exc:
        for _, dest, staged in reversed(written):
            try:
                if staged is not None:
                    shutil.copy2(staged, dest)
                elif os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
        if isinstance(exc, OpError):
            raise
        raise OpError("extract_failed") from exc
