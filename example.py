"""Example script demonstrating Star Foundry usage.

This script shows how to connect to MongoDB and retrieve all stars
from the repository.
"""

from dotenv import load_dotenv
import os
from star_foundry import MongoStarRepository


def main() -> None:
    """Main function to demonstrate MongoStarRepository usage.

    Loads environment variables, connects to MongoDB, and retrieves all stars.
    """
    load_dotenv()

    MONGO_URL = os.getenv("MONGO_URL")
    MONGO_DB = os.getenv("MONGO_DB")

    repo = MongoStarRepository(uri=MONGO_URL, db_name=MONGO_DB)
    result = repo.find_all()
    print(result)


if __name__ == "__main__":
    main()
