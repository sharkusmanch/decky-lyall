MESSAGES = {
    "network_offline": "No connection — using cached data",
    "verify_failed": "Download failed verification — try Refresh",
    "no_asset": "No downloadable release for this fix",
    "extract_failed": "Install failed — game files restored",
    "game_running": "Close the game before installing",
    "already_in_progress": "Another operation is running for this game",
    "needs_curation": "Awaiting catalog data for this game",
    "not_found": "Unknown mod or game",
    "unexpected": "Something went wrong — check the Decky log",
}


class OpError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or MESSAGES.get(code, MESSAGES["unexpected"])
        super().__init__(self.message)


def fail(code, message=None):
    return {"ok": False, "code": code,
            "message": message or MESSAGES.get(code, MESSAGES["unexpected"])}


def ok(**fields):
    return {"ok": True, **fields}
