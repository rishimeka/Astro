from pathlib import Path
from star_foundry.loader.star_loader import StarLoader


def test_load_fixtures():
    base = Path(__file__).parent.parent / "fixtures"
    loader = StarLoader(base)
    stars = loader.load_all()
    ids = {s.id for s in stars}
    assert "astro.ic.base.v1" in ids
    assert "astro.research.market.v1" in ids
    # we provided 5 fixtures
    assert len(stars) == 5
