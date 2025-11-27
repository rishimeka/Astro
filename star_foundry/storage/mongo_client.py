from __future__ import annotations

from typing import Optional
from pymongo import MongoClient


def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    """Return a pymongo MongoClient.

    If no `uri` is provided, default to localhost standard port.
    """
    if uri:
        return MongoClient(uri)
    return MongoClient("mongodb://localhost:27017")
