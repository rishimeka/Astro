import pytest
from star_foundry.models import Star, StarMetadata, ContentType
from star_foundry.validator.star_validator import StarValidator, ValidationError


def make_star(sid: str):
    meta = StarMetadata(
        description="d",
        content_type=ContentType.markdown,
        tags=[],
        version="v1",
        created_by="t",
        created_on="2025-01-01T00:00:00",
        updated_by="t",
        updated_on="2025-01-01T00:00:00",
    )
    return Star(id=sid, name=sid, metadata=meta, content="c", references=[], tools=[], parents=[])


def test_validator_duplicate_ids():
    a = make_star("same")
    b = make_star("same")
    with pytest.raises(ValidationError):
        StarValidator.validate([a, b])
