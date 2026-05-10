import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from south_tyrol_tourism.exceptions import APIError
from south_tyrol_tourism.pipeline import (
    _get_rooms,
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


def test_parse_entry_counts_rooms(sample_api_entry: dict) -> None:
    result = _parse_entry(sample_api_entry)
    assert result["AccoRoomInfo"] == 2


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


def test_parse_entry_null_room_info() -> None:
    entry: dict = {"Id": "Y", "AccoRoomInfo": None}
    result = _parse_entry(entry)
    assert result["AccoRoomInfo"] is None


def test_parse_entry_broken_location_info() -> None:
    entry: dict = {"Id": "Z", "LocationInfo": {"RegionInfo": None}}
    result = _parse_entry(entry)
    assert result["LocationInfo"] is None


# --- _get_rooms ---


def _mock_urlopen(rooms: list[dict]) -> MagicMock:
    body = json.dumps(rooms).encode()
    mock_response = MagicMock()
    mock_response.read.return_value = body
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_response)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def test_get_rooms_returns_correct_totals() -> None:
    rooms = [
        {"RoomQuantity": 3, "Roommax": 2},
        {"RoomQuantity": 2, "Roommax": 4},
    ]
    target = "south_tyrol_tourism.pipeline.urllib.request.urlopen"
    with patch(target, return_value=_mock_urlopen(rooms)):
        result = _get_rooms("ABC123")
    assert result == ("ABC123", 5, 3 * 2 + 2 * 4)


def test_get_rooms_single_room() -> None:
    rooms = [{"RoomQuantity": 1, "Roommax": 3}]
    target = "south_tyrol_tourism.pipeline.urllib.request.urlopen"
    with patch(target, return_value=_mock_urlopen(rooms)):
        result = _get_rooms("SINGLE")
    assert result == ("SINGLE", 1, 3)


def test_get_rooms_raises_api_error_on_network_failure() -> None:
    with patch(
        "south_tyrol_tourism.pipeline.urllib.request.urlopen",
        side_effect=OSError("connection refused"),
    ):
        with pytest.raises(APIError, match="FAIL"):
            _get_rooms("FAIL")


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
