"""Export the administration API subset without connecting to a database."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from backend.app.main import app

    schema = app.openapi()
    paths = {key: value for key, value in schema["paths"].items()
             if key.startswith("/api/v2/admin/")}
    selected = {}

    def collect(value):
        if isinstance(value, dict):
            ref = value.get("$ref", "")
            prefix = "#/components/schemas/"
            if ref.startswith(prefix):
                name = ref[len(prefix):]
                if name not in selected:
                    selected[name] = schema["components"]["schemas"][name]
                    collect(selected[name])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(paths)
    output = {"openapi": schema["openapi"], "info": {
        "title": "CareBalance administration API subset",
        "version": schema["info"]["version"],
        "description": "Additive administration endpoints on schema 0005. Generated from application routers; session, CSRF, persisted permissions and server scope apply. This is a reference, not runtime or clinical acceptance."},
        "paths": paths, "components": {"schemas": dict(sorted(selected.items()))}}
    target = ROOT / "docs/admin/openapi-0005.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"paths": len(paths), "schemas": len(selected), "database_connections": 0}))


if __name__ == "__main__":
    main()
