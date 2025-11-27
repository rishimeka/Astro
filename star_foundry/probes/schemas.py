from __future__ import annotations

from typing import List
from pydantic import BaseModel
from ..models import Star as StarModel


class StarSummary(BaseModel):
    id: str
    name: str
    metadata: dict


class StarDetails(BaseModel):
    id: str
    name: str
    metadata: dict
    content: str
    references: List[str]


class ListStarsOutput(BaseModel):
    stars: List[StarSummary]


class GetStarOutput(BaseModel):
    star: StarDetails


class SearchStarsOutput(BaseModel):
    results: List[StarSummary]
