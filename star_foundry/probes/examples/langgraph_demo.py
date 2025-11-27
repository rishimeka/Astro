"""Minimal demo showing ProbeBay + foundry probes usage.

Run as a script to load fixture stars and list them via the probe.
"""

import asyncio
from ...loader.star_loader import StarLoader
from ...registry.star_registry import StarRegistry
from ...probe_bay import ProbeBay
from ..foundry_probes import ListStarsProbe, GetStarProbe, SearchByTagProbe


async def main():
    loader = StarLoader("./star_foundry/fixtures")
    stars = loader.load_all()
    registry = StarRegistry()
    for s in stars:
        registry.add(s)

    bay = ProbeBay()
    bay.register(ListStarsProbe(registry))
    bay.register(GetStarProbe(registry))
    bay.register(SearchByTagProbe(registry))

    # list
    res = await bay.run("foundry.list_stars")
    print(f"Found {len(res.stars)} stars")

    # try a tag search
    if res.stars:
        example_tag = next((t for t in res.stars[0].metadata.get("tags", [])), None)
        if example_tag:
            tag_res = await bay.run("foundry.search_by_tag", tag=example_tag)
            print(f"Search by tag '{example_tag}' -> {len(tag_res.results)} result(s)")


if __name__ == "__main__":
    asyncio.run(main())
