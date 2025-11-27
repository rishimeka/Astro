import pytest
from pathlib import Path
from star_foundry.parsers import markdown_parser as mdp
from star_foundry.parsers.markdown_parser import parse_markdown
from star_foundry.models import ContentType


def test_normalize_content_type():
    assert mdp._normalize_content_type(None) == ContentType.markdown
    assert mdp._normalize_content_type("md") == ContentType.markdown
    assert mdp._normalize_content_type("markdown") == ContentType.markdown
    assert mdp._normalize_content_type("xml") == ContentType.xml
    assert mdp._normalize_content_type("unknown") == ContentType.text


def test_parse_markdown_missing_id(tmp_path: Path):
    p = tmp_path / "bad.md"
    p.write_text("---\nname: NoID\n---\ncontent")
    with pytest.raises(ValueError):
        parse_markdown(p)


def test_parse_markdown_invalid_yaml(tmp_path: Path):
    p = tmp_path / "bad2.md"
    # invalid YAML (tabs or broken structure)
    p.write_text("---\n:id: [unclosed\n---\nbody")
    with pytest.raises(ValueError):
        parse_markdown(p)


def test_parse_markdown_content_extraction(tmp_path: Path):
    p = tmp_path / "good.md"
    p.write_text(
        "---\nid: astro.test.v1\nname: Good\ncontent_type: md\n---\n# Title\nBody content\n"
    )
    s = parse_markdown(p)
    assert s.id == "astro.test.v1"
    assert "# Title" in s.content
