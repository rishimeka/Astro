#!/usr/bin/env python3
"""
Remove max_tokens from configs - causing issues with TokenTrackingLLM wrapper.
Rely on directive optimization for token savings instead.
"""

import requests

API_BASE = "http://localhost:8000"

def update_star(star_id: str, config: dict):
    url = f"{API_BASE}/stars/{star_id}"
    response = requests.put(url, json={"config": config})
    return response.status_code == 200

def main():
    print("Removing max_tokens from star configs...")

    # Planning star
    update_star("star-007", {
        "planning_depth": 2,
        "temperature": 0.1,
    })
    print("  ✓ star-007 (planning)")

    # News gatherer
    update_star("star-009", {
        "temperature": 0.2,
    })
    print("  ✓ star-009 (news)")

    # Bull analyst
    update_star("star-010", {
        "temperature": 0.4,
    })
    print("  ✓ star-010 (bull)")

    # Bear analyst
    update_star("star-011", {
        "temperature": 0.4,
    })
    print("  ✓ star-011 (bear)")

    # Synthesis
    update_star("star-012", {
        "format": "markdown",
        "include_sources": True,
        "temperature": 0.2,
        "max_upstream_length": 2500,  # Keep this - it's for input truncation, not output
    })
    print("  ✓ star-012 (synthesis)")

    print("\n✓ Done! Will rely on directive optimization for token savings.")

if __name__ == "__main__":
    main()
