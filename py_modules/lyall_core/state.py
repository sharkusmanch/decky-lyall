from . import dlo


def build_rows(*, mods, installed, manifests, dlo_text, busy_map):
    """Rows for every (usable mod, installed game) pair.

    Status precedence: update_available > needs_launch_option > installed;
    needs_curation for flat mods without install_subdir; blocked_by names another
    mod already installed for the same game (two mods must not share a game dir).
    """
    by_key = {(m["appid"], m["mod_id"]): m for m in manifests}
    installed_mod_for_appid = {m["appid"]: m["mod_id"] for m in manifests}
    rows = []
    for mod_id, mod in mods.items():
        for game in mod.get("games", []):
            appid = game.get("steam_appid")
            inst = installed.get(appid)
            if not inst:
                continue
            man = by_key.get((appid, mod_id))
            latest = mod.get("derived_release")
            other = installed_mod_for_appid.get(appid)
            blocked_by = other if (man is None and other) else None

            if man is not None:
                if man["version"] != latest:
                    status = "update_available"
                elif man.get("launch_option_handled") == "manual_pending":
                    status = "needs_launch_option"
                else:
                    status = "installed"
            elif mod["zip_layout"] == "flat" and not game.get("install_subdir"):
                status = "needs_curation"
            else:
                status = "not_installed"

            rows.append({
                "appid": appid, "mod_id": mod_id, "name": inst["name"],
                "install_path": inst["install_path"],
                "installed_version": man["version"] if man else None,
                "latest_version": latest,
                "wine_dll_override": mod["wine_dll_override"], "loader": mod["loader"],
                "status": status,
                "override_status": dlo.override_status(dlo_text, mod_id, appid),
                "busy": busy_map.get(appid), "blocked_by": blocked_by,
            })
    return rows
