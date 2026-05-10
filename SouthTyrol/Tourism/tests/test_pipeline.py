import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from south_tyrol_tourism.pipeline import (
    _parse_category,
    _parse_entry,
    prepare_dirs,
)

# --- _parse_category ---


@pytest.mark.parametrize(
    ("x", "expected"),
    [
        ("3sstars", ("3s", "stars")),
        ("4sstars", ("4s", "stars")),
        ("4stars", ("4", "stars")),
        ("2suns", ("2", "suns")),
        ("3flowers", ("3", "flowers")),
        ("Not categorized", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_category(x: str | None, expected: tuple) -> None:
    assert _parse_category(x) == expected


# --- _parse_entry ---


def test_parse_entry_extracts_name_and_city(sample_api_entry: dict) -> None:
    result = _parse_entry(sample_api_entry)
    assert result["Name"] == "Hotel Test"
    assert result["City"] == "Merano"


def test_parse_entry_extracts_id_and_category(sample_api_entry: dict) -> None:
    result = _parse_entry(sample_api_entry)
    assert result["Id"] == "ABC123"
    assert result["AccoCategoryId"] == "3stars"


def test_parse_entry_extracts_location(sample_api_entry: dict) -> None:
    result = _parse_entry(sample_api_entry)
    assert result["LocationInfo"] == "Meran"


def test_parse_entry_no_file_field(sample_api_entry: dict) -> None:
    result = _parse_entry(sample_api_entry)
    assert "file" not in result


def test_parse_entry_null_acco_detail() -> None:
    entry: dict = {"Id": "X", "AccoDetail": None, "LocationInfo": None}
    result = _parse_entry(entry)
    assert result["Name"] is None
    assert result["City"] is None
    assert result["LocationInfo"] is None


def test_parse_entry_broken_location_info() -> None:
    entry: dict = {"Id": "Z", "LocationInfo": {"RegionInfo": None}}
    result = _parse_entry(entry)
    assert result["LocationInfo"] is None


# --- prepare_dirs ---


def test_prepare_dirs_creates_all_directories(tmp_path: Path) -> None:
    new_dirs = [tmp_path / "a", tmp_path / "b" / "c"]
    prepare_dirs(dirs=new_dirs)
    for d in new_dirs:
        assert d.is_dir()


def test_prepare_dirs_is_idempotent(tmp_path: Path) -> None:
    new_dirs = [tmp_path / "x"]
    prepare_dirs(dirs=new_dirs)
    prepare_dirs(dirs=new_dirs)  # should not raise
    assert (tmp_path / "x").is_dir()


# --- download_accommodations resumability ---


def _make_urlopen_json(payload: dict) -> MagicMock:
    body = json.dumps(payload).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_resp)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def test_download_accommodations_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import south_tyrol_tourism.pipeline as pipeline_mod
    from south_tyrol_tourism.config import Settings

    custom = Settings(data_dir=tmp_path)
    custom.main_call_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pipeline_mod, "settings", custom)

    next_url = "https://example.com/page2"
    (custom.main_call_dir / "page_0.json").write_text(
        json.dumps({"Items": [{"Id": "A"}], "NextPage": next_url})
    )
    page2_data = {"Items": [{"Id": "B"}], "NextPage": None}

    called_urls: list[str] = []

    def fake_urlopen(url: str, **_: object) -> MagicMock:
        called_urls.append(url)
        return _make_urlopen_json(page2_data)

    with patch("south_tyrol_tourism.pipeline.urllib.request.urlopen", side_effect=fake_urlopen):
        pipeline_mod.download_accommodations()

    assert called_urls == [next_url]
    items = json.loads(custom.raw_accommodation_file.read_text())
    assert {it["Id"] for it in items} == {"A", "B"}


def test_download_accommodations_already_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import south_tyrol_tourism.pipeline as pipeline_mod
    from south_tyrol_tourism.config import Settings

    custom = Settings(data_dir=tmp_path)
    custom.main_call_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(pipeline_mod, "settings", custom)

    (custom.main_call_dir / "page_0.json").write_text(
        json.dumps({"Items": [{"Id": "A"}], "NextPage": None})
    )

    with patch("south_tyrol_tourism.pipeline.urllib.request.urlopen") as mock_open:
        pipeline_mod.download_accommodations()

    mock_open.assert_not_called()
    assert custom.raw_accommodation_file.exists()


