import asyncio
from star_foundry.loader.star_loader import StarLoader
from star_foundry.registry.star_registry import StarRegistry
from star_foundry.probes.foundry_probes import GetStarProbe


def test_get_star_probe_returns_star():
    loader = StarLoader("./star_foundry/fixtures")
    stars = loader.load_all()
    assert len(stars) > 0
    registry = StarRegistry()
    for s in stars:
        registry.add(s)

    pid = stars[0].id
    probe = GetStarProbe(registry)
    res = asyncio.get_event_loop().run_until_complete(probe.run(id=pid))
    assert hasattr(res, "star")
    # `star` is a Pydantic model (StarDetails) so use attribute access
    assert getattr(res.star, "id", None) == pid
