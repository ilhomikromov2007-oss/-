#!/usr/bin/env python3
import ast, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
INDEX = ROOT / "extera-plugins.json"
FIELDS = ("id", "name", "description", "author", "version", "icon", "app_version", "sdk_version", "requirements", "category")
REPOSITORY = {
    "schema": 1,
    "name": "Turbo AyuGram Plugins",
    "description": "Plugins for AyuGram",
    "author": "@ilhomikromov2007-oss",
    "homepage": "https://github.com/ilhomikromov2007-oss/-"
}
def main():
    entries = []
    for path in sorted(PLUGINS_DIR.rglob("*.plugin")):
        meta = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if key.startswith("__") and key.endswith("__") and key[2:-2] in FIELDS:
                    meta[key[2:-2]] = ast.literal_eval(node.value)
        missing = [k for k in ("id", "name", "version") if not meta.get(k)]
        if missing:
            raise SystemExit(f"{path}: missing {', '.join(missing)}")
        data = path.read_bytes()
        entries.append({**meta, "file": path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    ids = [p["id"] for p in entries]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate plugin ids")
    INDEX.write_text(json.dumps({**REPOSITORY, "plugins": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(entries)} plugin(s)")
if __name__ == "__main__":
    main()
