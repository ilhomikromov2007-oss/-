#!/usr/bin/env python3
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
INDEX = ROOT / "extera-plugins.json"
FIELDS = ("id", "name", "description", "author", "version", "icon",
          "app_version", "sdk_version", "requirements", "category")
REPOSITORY = {
    "schema": 1,
    "name": "Turbo AyuGram Plugins",
    "description": "Plugins for AyuGram",
    "author": "@ilhomikromov2007-oss",
    "homepage": "https://github.com/ilhomikromov2007-oss/-",
}
META_LINE = re.compile(r"^__(?P<key>[a-z_]+)__\\s*=\\s*(?P<value>.+?)\\s*$")


def read_metadata(path):
    """Read only top-level metadata assignments; plugin bodies may contain
    Android/PyJNI code that is not valid CPython syntax.
    """
    metadata = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = META_LINE.match(line)
        if not match:
            continue
        key = match.group("key")
        if key not in FIELDS:
            continue
        try:
            metadata[key] = ast.literal_eval(match.group("value"))
        except (SyntaxError, ValueError) as exc:
            raise SystemExit(f"{path}: invalid metadata value for __{key}__: {exc}")
    return metadata


def main():
    entries = []
    for path in sorted(PLUGINS_DIR.rglob("*.plugin")):
        meta = read_metadata(path)
        missing = [key for key in ("id", "name", "version") if not meta.get(key)]
        if missing:
            raise SystemExit(f"{path}: missing {', '.join(missing)}")
        data = path.read_bytes()
        entries.append({
            **meta,
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate plugin ids")

    INDEX.write_text(
        json.dumps({**REPOSITORY, "plugins": entries}, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(f"Indexed {len(entries)} plugin(s)")


if __name__ == "__main__":
    main()
