#!/usr/bin/env python3
"""
Update synthesis star configuration for optimizations.
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
    print("UPDATING SYNTHESIS STAR CONFIGURATION")
    print("=" * 60)
    print()

    # Update synthesis star with optimizations
    synthesis_config = {
        "format": "markdown",
        "include_sources": True,
        "temperature": 0.2,  # Lower temperature for synthesis (was 0.3 hardcoded)
        "max_tokens": 2000,  # Limit synthesis output
        "max_upstream_length": 2000,  # Truncate upstream outputs to 2000 chars each
    }

    if update_star("star-012", synthesis_config):
        print("\n✓ Synthesis star configuration updated!")
        print("\nNew config:")
        print(f"  - temperature: 0.2 (lower for more focused synthesis)")
        print(f"  - max_tokens: 2000 (limit synthesis output)")
        print(f"  - max_upstream_length: 2000 (truncate each upstream output)")
        print("\nExpected improvements:")
        print("  - Reduced input tokens: ~40-50% (less upstream context)")
        print("  - Reduced output tokens: ~30% (max_tokens limit)")
        print("  - Better quality: Lower temperature = more focused synthesis")
        return 0
    else:
        print("\n✗ Failed to update synthesis star")
        return 1

if __name__ == "__main__":
    exit(main())
