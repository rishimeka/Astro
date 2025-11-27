from __future__ import annotations

from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from ..models import Star, StarMetadata, ContentType


def _text_of(elem: ET.Element | None) -> str | None:
    return elem.text.strip() if elem is not None and elem.text else None


def parse_xml(file_path: str | Path) -> Star:
    p = Path(file_path)
    tree = ET.parse(p)
    root = tree.getroot()

    # Simple expected structure: <star><id>..</id><name>..</name><metadata>...</metadata><content>..</content></star>
    sid = _text_of(root.find("id"))
    name = _text_of(root.find("name"))
    if not sid or not name:
        raise ValueError(f"XML star {file_path} must contain <id> and <name>")

    desc = _text_of(root.find("description")) or ""
    content_raw = _text_of(root.find("content")) or ""

    # metadata fields optional
    content_type_raw = _text_of(root.find("content_type"))
    tags = [t.text.strip() for t in root.findall("tags/tag") if t.text]
    version = _text_of(root.find("version")) or "v1"
    created_by = _text_of(root.find("created_by")) or "unknown"
    created_on = _text_of(root.find("created_on"))
    updated_by = _text_of(root.find("updated_by")) or created_by
    updated_on = _text_of(root.find("updated_on")) or created_on

    # default datetimes when missing
    created_on_val = created_on or datetime.utcnow()
    updated_on_val = updated_on or created_on_val

    # normalize content type
    ct = ContentType.markdown
    if content_type_raw and content_type_raw.lower() == "xml":
        ct = ContentType.xml

    metadata = StarMetadata(
        description=desc,
        content_type=ct,
        tags=tags,
        version=version,
        created_by=created_by,
        created_on=created_on_val,
        updated_by=updated_by,
        updated_on=updated_on_val,
    )

    references = [r.text.strip() for r in root.findall("references/ref") if r.text]

    star = Star(
        id=sid,
        name=name,
        metadata=metadata,
        content=content_raw,
        references=references,
        tools=[t.text.strip() for t in root.findall("tools/tool") if t.text],
        parents=[],
        file_path=str(p),
    )

    return star
