#!/usr/bin/env python3
"""Export the FastAPI OpenAPI document for tools such as Postman."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import app


def _ensure_root_tags(schema: dict) -> None:
    """Ensure the schema includes explicit tag metadata for Postman folder names."""
    tag_names: list[str] = []
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                for tag_name in operation.get("tags", []):
                    if tag_name and tag_name not in tag_names:
                        tag_names.append(tag_name)

    schema["tags"] = [{"name": tag_name, "description": tag_name} for tag_name in tag_names]


def main() -> None:
    """Write the current application schema to docs/x-HanJiang.postman-openapi.json."""
    output_path = Path(__file__).resolve().parent.parent / "docs" / "x-HanJiang.postman-openapi.json"
    schema = app.openapi()
    _ensure_root_tags(schema)
    schema.setdefault("servers", [{"url": "http://localhost:8000"}])
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(schema.get('paths', {}))} paths to {output_path}")


if __name__ == "__main__":
    main()
