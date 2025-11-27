from __future__ import annotations

from typing import Dict, Set, List
from collections import defaultdict
from ..models import Star


class DuplicateStarError(Exception):
    pass


class StarRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, Star] = {}
        self._name_to_id: Dict[str, str] = {}
        self._tags: Dict[str, Set[str]] = defaultdict(set)

    def add(self, star: Star) -> None:
        if star.id in self._by_id:
            raise DuplicateStarError(f"Duplicate star id: {star.id}")
        self._by_id[star.id] = star
        # map name -> id (overwrite allowed if same id)
        self._name_to_id[star.name] = star.id
        for t in getattr(star.metadata, "tags", []):
            self._tags[t].add(star.id)

    def get_by_id(self, sid: str) -> Star | None:
        return self._by_id.get(sid)

    def get_by_name(self, name: str) -> Star | None:
        sid = self._name_to_id.get(name)
        return self._by_id.get(sid) if sid else None

    def search_by_tag(self, tag: str) -> List[Star]:
        ids = self._tags.get(tag, set())
        return [self._by_id[i] for i in ids]

    def all_metadata(self) -> List[dict]:
        return [s.metadata.model_dump() for s in self._by_id.values()]

    def all_ids(self) -> List[str]:
        return list(self._by_id.keys())
