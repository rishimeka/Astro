from __future__ import annotations

from typing import List
from ..registry.star_registry import StarRegistry
from .probe_base import AbstractProbe
from .schemas import StarSummary, StarDetails, ListStarsOutput, GetStarOutput, SearchStarsOutput


class ListStarsProbe(AbstractProbe):
    id = "foundry.list_stars"
    description = "List metadata summaries for all stars"
    input_schema = None
    output_schema = ListStarsOutput

    async def _run_impl(self, validated_input=None):
        # Build summaries by iterating all ids to ensure id/name are present
        ids = self.registry.all_ids()
        stars = []
        for sid in ids:
            s = self.registry.get_by_id(sid)
            if not s:
                continue
            meta = s.metadata.model_dump() if hasattr(s.metadata, "model_dump") else s.metadata.dict()
            stars.append(StarSummary(id=s.id, name=s.name, metadata=meta))
        return {"stars": stars}


class GetStarProbe(AbstractProbe):
    id = "foundry.get_star"
    description = "Return full star details by id"
    # input schema: expect {'id': str}
    class InputModel(__import__("pydantic").BaseModel):
        id: str

    input_schema = InputModel
    output_schema = GetStarOutput

    async def _run_impl(self, validated_input=None):
        sid = validated_input.id
        star = self.registry.get_by_id(sid)
        if not star:
            raise KeyError(f"Star not found: {sid}")
        data = {
            "id": star.id,
            "name": star.name,
            "metadata": star.metadata.model_dump() if hasattr(star.metadata, "model_dump") else star.metadata.dict(),
            "content": star.content,
            "references": star.references,
        }
        return {"star": data}


class GetChildrenProbe(AbstractProbe):
    id = "foundry.get_children"
    description = "Return direct referenced stars for a given star id"

    class InputModel(__import__("pydantic").BaseModel):
        id: str

    input_schema = InputModel
    output_schema = SearchStarsOutput

    async def _run_impl(self, validated_input=None):
        sid = validated_input.id
        star = self.registry.get_by_id(sid)
        if not star:
            raise KeyError(f"Star not found: {sid}")
        results = []
        for ref in getattr(star, "references", []):
            s = self.registry.get_by_id(ref)
            if s:
                results.append(StarSummary(id=s.id, name=s.name, metadata=s.metadata.model_dump() if hasattr(s.metadata, "model_dump") else s.metadata.dict()))
        return {"results": results}


class SearchByTagProbe(AbstractProbe):
    id = "foundry.search_by_tag"
    description = "Search stars by tag"

    class InputModel(__import__("pydantic").BaseModel):
        tag: str

    input_schema = InputModel
    output_schema = SearchStarsOutput

    async def _run_impl(self, validated_input=None):
        tag = validated_input.tag
        matches = self.registry.search_by_tag(tag)
        results = []
        for s in matches:
            results.append(StarSummary(id=s.id, name=s.name, metadata=s.metadata.model_dump() if hasattr(s.metadata, "model_dump") else s.metadata.dict()))
        return {"results": results}
