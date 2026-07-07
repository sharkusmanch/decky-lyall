import json
import os

# ~/.dlo/settings.json is DLO-internal state (verified at v1.12), NOT a contract.
# Anything unexpected must degrade to "unknown"; "unknown" never surfaces warnings.


def settings_path(user_home):
    return os.path.join(user_home, ".dlo", "settings.json")


def read_settings_text(user_home):
    try:
        with open(settings_path(user_home), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def override_status(settings_text, mod_id, appid):
    if settings_text is None:
        return "unknown"
    try:
        data = json.loads(settings_text)
        option_id = f"lyall-{mod_id}"
        options = data.get("launchOptions") or []
        if not any(o.get("id") == option_id for o in options):
            return "not_registered"
        profile = (data.get("profiles") or {}).get(str(appid)) or {}
        state = profile.get("state") or {}
        return "registered_enabled" if state.get(option_id) else "registered_disabled"
    except (ValueError, AttributeError, TypeError):
        return "unknown"
