from lyall_core import iniconfig

SAMPLE = """; ClairObscurFix configuration
[Fix Settings]
; Enable the fix
Enabled = true

[Custom Resolution]
Width = 1280
Height = 800
; Aspect ratio note
UseCustomRes = false
Label = Steam Deck
"""

BEPINEX_SAMPLE = """## Settings file was created by plugin RaidouFix
[General]

# Setting type: Boolean
Enabled = true
"""


def test_parse_extracts_entries_with_sections():
    entries = iniconfig.parse(SAMPLE)
    assert {"section": "Fix Settings", "key": "Enabled", "value": "true"} in [
        {k: e[k] for k in ("section", "key", "value")} for e in entries]
    by_key = {(e["section"], e["key"]): e["value"] for e in entries}
    assert by_key[("Custom Resolution", "Width")] == "1280"
    assert by_key[("Custom Resolution", "Label")] == "Steam Deck"
    assert len(entries) == 5  # comments and blanks are not entries


def test_parse_bepinex_cfg_hash_comments():
    entries = iniconfig.parse(BEPINEX_SAMPLE)
    assert [(e["section"], e["key"], e["value"]) for e in entries] == [
        ("General", "Enabled", "true")]


def test_set_value_preserves_everything_else():
    out = iniconfig.set_value(SAMPLE, "Custom Resolution", "Width", "1920")
    assert "Width = 1920" in out
    # all comments, blank lines, and other values untouched
    assert out.count("\n") == SAMPLE.count("\n")
    assert "; Aspect ratio note" in out
    assert "Height = 800" in out
    assert "Enabled = true" in out


def test_set_value_targets_correct_section():
    text = "[A]\nEnabled = true\n[B]\nEnabled = true\n"
    out = iniconfig.set_value(text, "B", "Enabled", "false")
    assert out == "[A]\nEnabled = true\n[B]\nEnabled = false\n"


def test_set_value_missing_key_raises():
    import pytest
    from lyall_core.errors import OpError
    with pytest.raises(OpError):
        iniconfig.set_value(SAMPLE, "Fix Settings", "Nope", "1")


def test_sniff_type():
    assert iniconfig.sniff_type("true") == "bool"
    assert iniconfig.sniff_type("False") == "bool"
    assert iniconfig.sniff_type("1280") == "number"
    assert iniconfig.sniff_type("1.5") == "number"
    assert iniconfig.sniff_type("Steam Deck") == "string"
