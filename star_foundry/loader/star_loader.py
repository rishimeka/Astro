from pathlib import Path
from typing import List
from ..models import Star
from ..parsers.markdown_parser import parse_markdown
from ..parsers.xml_parser import parse_xml


class StarLoader:
    SUPPORTED = {".md": parse_markdown, ".markdown": parse_markdown, ".xml": parse_xml}

    def __init__(self, base_path: str | Path):
        self.base = Path(base_path)

    def load_all(self) -> List[Star]:
        if not self.base.exists():
            return []
        stars: list[Star] = []
        for p in self.base.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            parser = self.SUPPORTED.get(ext)
            if not parser:
                continue
            try:
                star = parser(p)
                stars.append(star)
            except Exception as exc:
                # surface loader errors as ValueError for tests to inspect
                raise ValueError(f"Failed loading {p}: {exc}") from exc
        return stars
