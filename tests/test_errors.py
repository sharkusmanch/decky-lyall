from lyall_core.errors import OpError, fail, ok


def test_fail_uses_default_message():
    env = fail("game_running")
    assert env == {"ok": False, "code": "game_running",
                   "message": "Close the game before installing"}


def test_fail_unknown_code_falls_back():
    env = fail("bogus")
    assert env["ok"] is False and env["message"]


def test_ok_merges_fields():
    assert ok(accepted=True) == {"ok": True, "accepted": True}


def test_operror_carries_code_and_message():
    e = OpError("verify_failed")
    assert e.code == "verify_failed" and "verification" in e.message
