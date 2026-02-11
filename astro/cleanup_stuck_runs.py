"""Clean up stuck runs that have been running for too long."""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_stuck_runs():
    """Mark runs as failed if they've been running for more than 2 hours."""
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "astro")

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    runs_collection = db["runs"]

    # Find runs that are still "running" but started more than 2 hours ago
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=2)

    # Query for stuck runs
    stuck_runs = await runs_collection.find({
        "status": "running",
        "started_at": {"$lt": cutoff_time.isoformat()}
    }).to_list(length=None)

    if not stuck_runs:
        print("No stuck runs found.")
        return

    print(f"Found {len(stuck_runs)} stuck runs:")
    for run in stuck_runs:
        print(f"  - {run['id']}: started {run['started_at']}")

    # Update them to failed status
    result = await runs_collection.update_many(
        {
            "status": "running",
            "started_at": {"$lt": cutoff_time.isoformat()}
        },
        {
            "$set": {
                "status": "failed",
                "error": "Run timed out - exceeded 2 hour limit",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    print(f"\nUpdated {result.modified_count} runs to 'failed' status.")

    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_stuck_runs())
