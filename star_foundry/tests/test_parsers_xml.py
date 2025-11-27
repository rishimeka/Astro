import pytest
from pathlib import Path
from star_foundry.parsers.xml_parser import parse_xml


def test_parse_xml_success(tmp_path: Path):
    p = tmp_path / "star.xml"
    p.write_text(
        """
<star>
  <id>astro.xml.test.v1</id>
  <name>XML Test</name>
  <description>desc</description>
  <content>xml content</content>
  <content_type>xml</content_type>
  <tags>
    <tag>a</tag>
    <tag>b</tag>
  </tags>
  <references>
    <ref>astro.ic.base.v1</ref>
  </references>
  <tools>
    <tool>tool1</tool>
  </tools>
  <version>v2</version>
  <created_by>me</created_by>
  <created_on>2025-05-01T00:00:00</created_on>
</star>
"""
    )
    s = parse_xml(p)
    assert s.id == "astro.xml.test.v1"
    assert s.metadata.content_type.name == "xml"
    assert "a" in s.metadata.tags
    assert s.references == ["astro.ic.base.v1"]


def test_parse_xml_missing_fields(tmp_path: Path):
    p = tmp_path / "bad.xml"
    p.write_text("<star><name>NoID</name></star>")
    with pytest.raises(ValueError):
        parse_xml(p)
