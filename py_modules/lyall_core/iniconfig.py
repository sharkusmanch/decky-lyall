import re

from .errors import OpError

# Handles Lyall's .ini files and BepInEx .cfg files: [Section] headers,
# "Key = Value" pairs, comment lines starting with ; # or //.
_SECTION_RE = re.compile(r"^\s*\[(.+?)\]\s*$")
_KV_RE = re.compile(r"^(\s*)([^=;#\[\]]+?)(\s*=\s*)(.*?)(\s*)$")
_COMMENT_RE = re.compile(r"^\s*(;|#|//)")


def parse(text):
    """Return [{section, key, value, line}] — comments/blanks are skipped."""
    entries = []
    section = None
    for i, line in enumerate(text.splitlines()):
        if not line.strip() or _COMMENT_RE.match(line):
            continue
        m = _SECTION_RE.match(line)
        if m:
            section = m.group(1)
            continue
        m = _KV_RE.match(line)
        if m:
            entries.append({"section": section, "key": m.group(2).strip(),
                            "value": m.group(4), "line": i})
    return entries


def set_value(text, section, key, value):
    """Rewrite exactly one Key = Value line, preserving all other content."""
    for entry in parse(text):
        if entry["section"] == section and entry["key"] == key:
            lines = text.splitlines(keepends=True)
            old = lines[entry["line"]]
            m = _KV_RE.match(old.rstrip("\r\n"))
            eol = old[len(old.rstrip("\r\n")):]
            lines[entry["line"]] = f"{m.group(1)}{m.group(2)}{m.group(3)}{value}{eol}"
            return "".join(lines)
    raise OpError("not_found", f"no setting [{section}] {key}")


def sniff_type(value):
    if value.strip().lower() in ("true", "false"):
        return "bool"
    try:
        float(value.strip())
        return "number"
    except ValueError:
        return "string"
