from star_foundry.registry.star_registry import StarRegistry
from star_foundry.models import Star, StarMetadata, ContentType


def make_star(sid: str, name: str, tags=None):
    if tags is None:
        tags = []
    meta = StarMetadata(
        description="d",
        content_type=ContentType.markdown,
        tags=tags,
        version="v1",
        created_by="t",
        created_on="2025-01-01T00:00:00",
        updated_by="t",
        updated_on="2025-01-01T00:00:00",
    )
    return Star(id=sid, name=name, metadata=meta, content="c", references=[], tools=[], parents=[])


def test_registry_basic():
    r = StarRegistry()
    a = make_star("a", "Alice", ["x"])
    b = make_star("b", "Bob", ["x", "y"])
    r.add(a)
    r.add(b)
    assert r.get_by_id("a").name == "Alice"
    assert r.get_by_name("Bob").id == "b"
    by_tag = r.search_by_tag("x")
    assert {s.id for s in by_tag} == {"a", "b"}
    assert len(r.all_metadata()) == 2
