from __future__ import annotations

from typing import List
from pymongo.collection import Collection
from ..models import Star
import warnings


class MongoStarLoader:
    def __init__(self, mongo_collection: Collection):
        self.collection = mongo_collection

    def load_all(self) -> List[Star]:
        docs = list(self.collection.find({}))
        stars: list[Star] = []
        for d in docs:
            # drop mongo's _id if present
            if "_id" in d:
                d = {k: v for k, v in d.items() if k != "_id"}
            try:
                # pydantic v2 model_validate preferred if available
                if hasattr(Star, "model_validate"):
                    star = Star.model_validate(d)
                else:
                    star = Star(**d)
                stars.append(star)
            except Exception as exc:
                # Surface validation issues but continue loading others
                warnings.warn(f"Failed validating star document: {exc}")
        return stars
