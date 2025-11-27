import pytest
from star_foundry.registry.star_registry import StarRegistry, DuplicateStarError
from star_foundry.tests.test_registry import make_star


def test_registry_duplicate_error():
    r = StarRegistry()
    a = make_star("dup", "Name")
    b = make_star("dup", "Name2")
    r.add(a)
    with pytest.raises(DuplicateStarError):
        r.add(b)
