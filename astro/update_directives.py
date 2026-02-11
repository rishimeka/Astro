#!/usr/bin/env python3
"""
Update directives with optimized content via API.
This script updates only the 5 directives used in const-001 without touching other data.
"""

import requests
import json
from optimized_directives import (
    DIR_006_OPTIMIZED,
    DIR_007_OPTIMIZED,
    DIR_008_OPTIMIZED,
    DIR_009_OPTIMIZED,
    DIR_010_OPTIMIZED,
)

API_BASE = "http://localhost:8000"

def update_directive(directive_id: str, content: str):
    """Update a directive's content via API."""
    url = f"{API_BASE}/directives/{directive_id}"
    payload = {"content": content}

    print(f"Updating {directive_id}...")
    response = requests.put(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        warnings = data.get("warnings", [])
        if warnings:
            print(f"  ✓ Updated with {len(warnings)} warnings:")
            for w in warnings:
                print(f"    - {w}")
        else:
            print(f"  ✓ Updated successfully")
        return True
    else:
        print(f"  ✗ Failed: {response.status_code}")
        print(f"    {response.text}")
        return False

def main():
    print("=" * 60)
    print("UPDATING DIRECTIVES WITH OPTIMIZED CONTENT")
    print("=" * 60)
    print()

    updates = [
        ("dir-006", DIR_006_OPTIMIZED, "News Gathering"),
        ("dir-007", DIR_007_OPTIMIZED, "Bull Case"),
        ("dir-008", DIR_008_OPTIMIZED, "Bear Case"),
        ("dir-009", DIR_009_OPTIMIZED, "Synthesis"),
        ("dir-010", DIR_010_OPTIMIZED, "Planning"),
    ]

    success_count = 0
    for directive_id, content, name in updates:
        if update_directive(directive_id, content):
            success_count += 1
        print()

    print("=" * 60)
    print(f"RESULTS: {success_count}/{len(updates)} directives updated")
    print("=" * 60)

    if success_count == len(updates):
        print("\n✓ All directives updated successfully!")
        print("\nExpected improvements:")
        print("  - Token reduction: ~72% (8,300 → 2,300 tokens)")
        print("  - Cost reduction: ~70%+ ($2.92 → <$1.00)")
        print("  - Time reduction: ~30-40%")
        return 0
    else:
        print(f"\n✗ {len(updates) - success_count} updates failed")
        return 1

if __name__ == "__main__":
    exit(main())
