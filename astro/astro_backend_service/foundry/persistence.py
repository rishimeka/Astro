"""MongoDB persistence layer using motor (async driver)."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from astro_backend_service.models import Constellation, Directive
from astro_backend_service.models.stars.base import BaseStar
from astro_backend_service.models.stars import (
    WorkerStar,
    PlanningStar,
    EvalStar,
    SynthesisStar,
    ExecutionStar,
    DocExStar,
)

T = TypeVar("T", bound=BaseModel)

# Star type mapping for deserialization
STAR_TYPE_MAP: Dict[str, Type[BaseStar]] = {
    "worker": WorkerStar,
    "planning": PlanningStar,
    "eval": EvalStar,
    "synthesis": SynthesisStar,
    "execution": ExecutionStar,
    "docex": DocExStar,
}


class FoundryPersistence:
    """MongoDB persistence operations for Foundry."""

    def __init__(self, mongo_uri: str, database_name: str = "astro"):
        """
        Initialize persistence layer.

        Args:
            mongo_uri: MongoDB connection URI
            database_name: Database name to use
        """
        self._client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(mongo_uri)
        self._db: AsyncIOMotorDatabase[Dict[str, Any]] = self._client[database_name]

        # Collection references
        self.directives = self._db["directives"]
        self.stars = self._db["stars"]
        self.constellations = self._db["constellations"]
        self.runs = self._db["runs"]

    async def close(self) -> None:
        """Close the MongoDB connection."""
        self._client.close()

    # =========================================================================
    # Directive Operations
    # =========================================================================

    async def create_directive(self, directive: Directive) -> None:
        """Insert directive into MongoDB."""
        doc = directive.model_dump()
        doc["_id"] = directive.id
        await self.directives.insert_one(doc)

    async def get_directive(self, id: str) -> Optional[Directive]:
        """Get directive by ID from MongoDB."""
        doc = await self.directives.find_one({"_id": id})
        if doc:
            doc.pop("_id", None)
            return Directive.model_validate(doc)
        return None

    async def list_directives(self) -> List[Directive]:
        """List all directives from MongoDB."""
        directives = []
        async for doc in self.directives.find():
            doc.pop("_id", None)
            directives.append(Directive.model_validate(doc))
        return directives

    async def update_directive(self, id: str, updates: Dict[str, Any]) -> bool:
        """Update directive in MongoDB. Returns True if updated."""
        result = await self.directives.update_one({"_id": id}, {"$set": updates})
        return result.modified_count > 0

    async def replace_directive(self, directive: Directive) -> bool:
        """Replace entire directive in MongoDB. Returns True if replaced."""
        doc = directive.model_dump()
        doc["_id"] = directive.id
        result = await self.directives.replace_one({"_id": directive.id}, doc)
        return result.modified_count > 0

    async def delete_directive(self, id: str) -> bool:
        """Delete directive from MongoDB. Returns True if deleted."""
        result = await self.directives.delete_one({"_id": id})
        return result.deleted_count > 0

    # =========================================================================
    # Star Operations
    # =========================================================================

    async def create_star(self, star: BaseStar) -> None:
        """Insert star into MongoDB."""
        doc = star.model_dump()
        doc["_id"] = star.id
        await self.stars.insert_one(doc)

    async def get_star(self, id: str) -> Optional[BaseStar]:
        """Get star by ID from MongoDB."""
        doc = await self.stars.find_one({"_id": id})
        if doc:
            doc.pop("_id", None)
            return self._deserialize_star(doc)
        return None

    async def list_stars(self) -> List[BaseStar]:
        """List all stars from MongoDB."""
        stars = []
        async for doc in self.stars.find():
            doc.pop("_id", None)
            star = self._deserialize_star(doc)
            if star:
                stars.append(star)
        return stars

    async def update_star(self, id: str, updates: Dict[str, Any]) -> bool:
        """Update star in MongoDB. Returns True if updated."""
        result = await self.stars.update_one({"_id": id}, {"$set": updates})
        return result.modified_count > 0

    async def replace_star(self, star: BaseStar) -> bool:
        """Replace entire star in MongoDB. Returns True if replaced."""
        doc = star.model_dump()
        doc["_id"] = star.id
        result = await self.stars.replace_one({"_id": star.id}, doc)
        return result.modified_count > 0

    async def delete_star(self, id: str) -> bool:
        """Delete star from MongoDB. Returns True if deleted."""
        result = await self.stars.delete_one({"_id": id})
        return result.deleted_count > 0

    def _deserialize_star(self, doc: Dict[str, Any]) -> Optional[BaseStar]:
        """Deserialize star document to correct Star subclass."""
        star_type = doc.get("type")
        if star_type and star_type in STAR_TYPE_MAP:
            return STAR_TYPE_MAP[star_type].model_validate(doc)
        return None

    # =========================================================================
    # Constellation Operations
    # =========================================================================

    async def create_constellation(self, constellation: Constellation) -> None:
        """Insert constellation into MongoDB."""
        doc = constellation.model_dump()
        doc["_id"] = constellation.id
        await self.constellations.insert_one(doc)

    async def get_constellation(self, id: str) -> Optional[Constellation]:
        """Get constellation by ID from MongoDB."""
        doc = await self.constellations.find_one({"_id": id})
        if doc:
            doc.pop("_id", None)
            return Constellation.model_validate(doc)
        return None

    async def list_constellations(self) -> List[Constellation]:
        """List all constellations from MongoDB."""
        constellations = []
        async for doc in self.constellations.find():
            doc.pop("_id", None)
            constellations.append(Constellation.model_validate(doc))
        return constellations

    async def update_constellation(self, id: str, updates: Dict[str, Any]) -> bool:
        """Update constellation in MongoDB. Returns True if updated."""
        result = await self.constellations.update_one({"_id": id}, {"$set": updates})
        return result.modified_count > 0

    async def replace_constellation(self, constellation: Constellation) -> bool:
        """Replace entire constellation in MongoDB. Returns True if replaced."""
        doc = constellation.model_dump()
        doc["_id"] = constellation.id
        result = await self.constellations.replace_one({"_id": constellation.id}, doc)
        return result.modified_count > 0

    async def delete_constellation(self, id: str) -> bool:
        """Delete constellation from MongoDB. Returns True if deleted."""
        result = await self.constellations.delete_one({"_id": id})
        return result.deleted_count > 0

    # =========================================================================
    # Run Operations
    # =========================================================================

    async def create_run(self, run: Dict[str, Any]) -> None:
        """Insert run into MongoDB."""
        doc = dict(run)
        doc["_id"] = run["id"]
        await self.runs.insert_one(doc)

    async def get_run(self, id: str) -> Optional[Dict[str, Any]]:
        """Get run by ID from MongoDB."""
        doc = await self.runs.find_one({"_id": id})
        if doc:
            doc.pop("_id", None)
            return dict(doc)
        return None

    async def list_runs(
        self, constellation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List runs, optionally filtered by constellation_id."""
        query = {}
        if constellation_id:
            query["constellation_id"] = constellation_id

        runs = []
        async for doc in self.runs.find(query).sort("started_at", -1):
            doc.pop("_id", None)
            runs.append(doc)
        return runs

    async def update_run(self, id: str, updates: Dict[str, Any]) -> bool:
        """Update run in MongoDB. Returns True if updated."""
        result = await self.runs.update_one({"_id": id}, {"$set": updates})
        return result.modified_count > 0

    # =========================================================================
    # Reference Checks
    # =========================================================================

    async def directive_referenced_by_stars(self, directive_id: str) -> List[str]:
        """Get list of star IDs that reference this directive."""
        star_ids = []
        async for doc in self.stars.find({"directive_id": directive_id}):
            star_ids.append(doc["_id"])
        return star_ids

    async def star_referenced_by_constellations(self, star_id: str) -> List[str]:
        """Get list of constellation IDs that reference this star."""
        constellation_ids = []
        async for doc in self.constellations.find({"nodes.star_id": star_id}):
            constellation_ids.append(doc["_id"])
        return constellation_ids
