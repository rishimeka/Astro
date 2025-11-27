from pathlib import Path
import pytest
from star_foundry.loader.star_loader import StarLoader


def test_loader_base_missing(tmp_path: Path):
    loader = StarLoader(tmp_path / "no_such_dir")
    assert loader.load_all() == []


def test_loader_unsupported_and_error(tmp_path: Path):
    # create unsupported .txt file
    t = tmp_path / "skip.txt"
    t.write_text("hello")

    # create invalid .md to trigger parser exception
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: NoID\n---\nbody")

    loader = StarLoader(tmp_path)
    # unsupported should be skipped, but bad.md triggers ValueError
    with pytest.raises(ValueError):
        loader.load_all()
