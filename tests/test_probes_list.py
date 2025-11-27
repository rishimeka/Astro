import asyncio
from star_foundry.loader.star_loader import StarLoader
from star_foundry.registry.star_registry import StarRegistry
from star_foundry.probes.foundry_probes import ListStarsProbe


def test_list_stars_probe_loads_fixtures():
    loader = StarLoader("./star_foundry/fixtures")
    stars = loader.load_all()
    registry = StarRegistry()
    for s in stars:
        registry.add(s)

    probe = ListStarsProbe(registry)
    res = asyncio.get_event_loop().run_until_complete(probe.run())
    assert hasattr(res, "stars")
    assert isinstance(res.stars, list)
    # at least one fixture should exist in repository
    assert len(res.stars) > 0
