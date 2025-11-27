from __future__ import annotations

from pathlib import Path
import yaml
import re
from typing import Any
from datetime import datetime
from ..models import Star, StarMetadata, ContentType


def _normalize_content_type(raw: str | None) -> ContentType:
    if not raw:
        return ContentType.markdown
    raw = raw.lower()
    if raw in ("md", "markdown"):
        return ContentType.markdown
    if raw in ("xml",):
        return ContentType.xml
    return ContentType.text


def parse_markdown(file_path: str | Path) -> Star:
    p = Path(file_path)
    text = p.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    content = text

    if text.startswith("---"):
        # split into ['', yaml, rest] when there are two leading '---' markers
        parts = re.split(r"^---\s*$", text, flags=re.M)
        # parts may include empty strings; attempt to find the YAML block as the first non-empty after leading marker
        if len(parts) >= 3:
            # parts[1] should be YAML block
            meta_raw = parts[1]
            try:
                meta = yaml.safe_load(meta_raw) or {}
            except Exception as e:
                raise ValueError(f"Invalid YAML frontmatter in {file_path}: {e}")
            # content is remaining after the YAML block
            # find the position of the second '---' separator to get raw content slice
            m = re.search(r"^---\s*$", text, flags=re.M)
            if m:
                # find next match after m.end()
                m2 = re.search(r"^---\s*$", text[m.end():], flags=re.M)
                if m2:
                    content = text[m.end() + m2.end():].lstrip("\n")
                else:
                    content = text[m.end():].lstrip("\n")

    # required top-level keys: id, name, plus metadata fields
    if "id" not in meta or "name" not in meta:
        raise ValueError(f"Frontmatter for {file_path} must include 'id' and 'name'")

    # ensure datetimes exist (pydantic will parse ISO strings or accept datetimes)
    created_on = meta.get("created_on") or datetime.utcnow()
    updated_on = meta.get("updated_on") or created_on

    metadata_payload = {
        "description": meta.get("description", ""),
        "content_type": _normalize_content_type(meta.get("content_type")),
        "tags": meta.get("tags", []),
        "version": meta.get("version", "v1"),
        "created_by": meta.get("created_by", "unknown"),
        "created_on": created_on,
        "updated_by": meta.get("updated_by", meta.get("created_by", "unknown")),
        "updated_on": updated_on,
    }

    metadata = StarMetadata(**metadata_payload)

    star = Star(
        id=str(meta["id"]),
        name=str(meta["name"]),
        metadata=metadata,
        content=content,
        references=meta.get("references", []),
        tools=meta.get("tools", []),
        parents=[],
        file_path=str(p),
    )

    return star
