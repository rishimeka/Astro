import pytest
from pathlib import Path
from star_foundry.loader.star_loader import StarLoader
from star_foundry.validator.star_validator import StarValidator, ValidationError


def test_validator_success():
    base = Path(__file__).parent.parent / "fixtures"
    loader = StarLoader(base)
    # only load base and financial for this test
    stars = [s for s in loader.load_all() if s.id in ("astro.ic.base.v1", "astro.research.market.v1")]
    assert len(stars) == 2
    # should not raise
    StarValidator.validate(stars)
    # parents populated: base should have market as child
    base_star = next(s for s in stars if s.id == "astro.ic.base.v1")
    assert "astro.research.market.v1" in base_star.parents


def test_validator_missing_ref():
    base = Path(__file__).parent.parent / "fixtures"
    loader = StarLoader(base)
    stars = [s for s in loader.load_all() if s.id == "astro.broken.missing.v1"]
    assert len(stars) == 1
    with pytest.raises(ValidationError):
        StarValidator.validate(stars)


def test_validator_cycle_detection():
    base = Path(__file__).parent.parent / "fixtures"
    loader = StarLoader(base)
    stars = [s for s in loader.load_all() if s.id in ("astro.cycle.a.v1", "astro.cycle.b.v1")]
    assert len(stars) == 2
    with pytest.raises(ValidationError):
        StarValidator.validate(stars)
