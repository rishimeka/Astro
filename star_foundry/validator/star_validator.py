from __future__ import annotations

from typing import List, Dict, Set
from ..models import Star


class ValidationError(Exception):
    pass


class StarValidator:
    @staticmethod
    def validate(stars: List[Star]) -> None:
        """Validate a list of stars for duplicates, missing refs and cycles.

        Populates `parents` for each Star in-place.
        Raises ValidationError with a summary message on failure.
        """
        id_map: Dict[str, Star] = {s.id: s for s in stars}

        # duplicates
        if len(id_map) != len(stars):
            # find duplicates
            seen = set()
            dup_ids = set()
            for s in stars:
                if s.id in seen:
                    dup_ids.add(s.id)
                seen.add(s.id)
            raise ValidationError(f"Duplicate IDs found: {sorted(dup_ids)}")

        # missing refs
        missing: Set[str] = set()
        for s in stars:
            for r in s.references:
                if r not in id_map:
                    missing.add(r)
        if missing:
            raise ValidationError(f"Missing referenced star IDs: {sorted(missing)}")

        # populate parents
        for s in stars:
            s.parents = []
        for s in stars:
            for r in s.references:
                id_map[r].parents.append(s.id)

        # cycle detection via DFS
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def dfs(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for nbr in id_map[node_id].references:
                if dfs(nbr):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        for sid in id_map:
            if dfs(sid):
                raise ValidationError("Cycle detected in star reference graph")
