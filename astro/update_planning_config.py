#!/usr/bin/env python3
"""
Update planning star configuration for optimizations.
"""

import requests
import json

API_BASE = "http://localhost:8000"

def update_star(star_id: str, config: dict):
    """Update a star's configuration via API."""
    url = f"{API_BASE}/stars/{star_id}"
    payload = {"config": config}

    print(f"Updating {star_id}...")
    response = requests.put(url, json=payload)

    if response.status_code == 200:
        print(f"  ✓ Updated successfully")
        return True
    else:
        print(f"  ✗ Failed: {response.status_code}")
        print(f"    {response.text}")
        return False

def main():
    print("=" * 60)
    print("UPDATING PLANNING STAR CONFIGURATION")
    print("=" * 60)
    print()

    # Update planning star with optimizations
    planning_config = {
        "planning_depth": 2,
        "temperature": 0.1,  # Very low temperature for structured planning
        "max_tokens": 1000,  # Limit plan output (just need JSON structure)
    }

    if update_star("star-007", planning_config):
        print("\n✓ Planning star configuration updated!")
        print("\nNew config:")
        print(f"  - temperature: 0.1 (very low for structured output)")
        print(f"  - max_tokens: 1000 (plans are short JSON)")
        print("\nExpected improvements:")
        print("  - Lower cost: Less output tokens")
        print("  - Better quality: Lower temperature = more consistent planning")
        return 0
    else:
        print("\n✗ Failed to update planning star")
        return 1

if __name__ == "__main__":
    exit(main())
