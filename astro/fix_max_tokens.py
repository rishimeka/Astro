#!/usr/bin/env python3
"""
Fix max_tokens values that are too restrictive.
"""

import requests

API_BASE = "http://localhost:8000"

def update_star(star_id: str, config: dict):
    """Update a star's configuration."""
    url = f"{API_BASE}/stars/{star_id}"
    response = requests.put(url, json={"config": config})
    return response.status_code == 200

def main():
    print("Adjusting max_tokens values...")

    # Bull analyst - increase from 3000 to 4000
    print("  - star-010 (bull): max_tokens 3000 → 4000")
    update_star("star-010", {
        "temperature": 0.4,
        "max_tokens": 4000  # Increased
    })

    # Bear analyst - increase from 3000 to 4000
    print("  - star-011 (bear): max_tokens 3000 → 4000")
    update_star("star-011", {
        "temperature": 0.4,
        "max_tokens": 4000  # Increased
    })

    # Synthesis - increase from 2000 to 3500
    print("  - star-012 (synthesis): max_tokens 2000 → 3500")
    update_star("star-012", {
        "format": "markdown",
        "include_sources": True,
        "temperature": 0.2,
        "max_tokens": 3500,  # Increased
        "max_upstream_length": 2500,  # Also increased from 2000
    })

    print("\n✓ Updated! Now more headroom while still limiting bloat.")

if __name__ == "__main__":
    main()
