import os


def game_running(install_path, proc_root="/proc"):
    """True if any process cmdline references the game's install path."""
    needle = install_path.encode()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return False
    for pid in pids:
        try:
            with open(os.path.join(proc_root, pid, "cmdline"), "rb") as f:
                if needle in f.read():
                    return True
        except OSError:
            continue
    return False
