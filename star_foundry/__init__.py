"""Star Foundry - Core module for managing Star entities.

This module provides the main data models and repository implementations
for working with Star objects in the system.
"""

from star_foundry.star import Star
from star_foundry.mongo_star_repo import MongoStarRepository
from star_foundry.registry import StarRegistry
from star_foundry.loader import StarLoader
from star_foundry.validator import StarValidator

# Conditionally import async repository (requires motor)
try:
    from star_foundry.async_star_repo import AsyncMongoStarRepository

    _ASYNC_AVAILABLE = True
except ImportError:
    AsyncMongoStarRepository = None
    _ASYNC_AVAILABLE = False

__all__ = [
    "Star",
    "MongoStarRepository",
    "StarRegistry",
    "StarLoader",
    "StarValidator",
]

if _ASYNC_AVAILABLE:
    __all__.append("AsyncMongoStarRepository")
