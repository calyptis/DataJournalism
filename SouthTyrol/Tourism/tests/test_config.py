from pathlib import Path

from south_tyrol_tourism.config import (
    VARIABLES_INFO,
    VARIABLES_INV,
    VARIABLES_PRETTY,
    Settings,
    settings,
)


def test_all_settings_paths_are_absolute() -> None:
    path_fields = [
        "data_dir", "plot_dir", "raw_data_dir", "api_calls_dir",
        "main_call_dir", "prepared_data_dir", "dashboard_data_dir",
        "population_shapefile", "province_shapefile",
        "raw_accommodation_file", "parsed_accommodation_file",
        "prepared_accommodation_file", "municipality_file",
    ]
    for field in path_fields:
        p = getattr(settings, field)
        assert isinstance(p, Path), f"settings.{field} must be a Path, got {type(p)}"
        assert p.is_absolute(), f"settings.{field} must be absolute"


def test_dirs_contains_only_paths() -> None:
    for d in settings.dirs:
        assert isinstance(d, Path)


def test_parquet_files_have_parquet_extension() -> None:
    parquet_fields = [
        "parsed_accommodation_file",
        "prepared_accommodation_file",
        "municipality_file",
    ]
    for field in parquet_fields:
        assert getattr(settings, field).suffix == ".parquet", (
            f"settings.{field} must end in .parquet"
        )


def test_raw_accommodation_file_is_json() -> None:
    assert settings.raw_accommodation_file.suffix == ".json"


def test_env_var_override_propagates_to_derived_paths(tmp_path: Path) -> None:
    custom = Settings(data_dir=tmp_path)
    assert custom.raw_data_dir == tmp_path / "raw_data"
    assert custom.prepared_data_dir == tmp_path / "prepared_data"
    assert custom.municipality_file == tmp_path / "dashboard_data" / "municipality.parquet"


def test_env_var_override_dirs_are_rooted_under_custom_data_dir(tmp_path: Path) -> None:
    custom = Settings(data_dir=tmp_path)
    for d in custom.dirs:
        if d != custom.plot_dir:
            assert str(d).startswith(str(tmp_path)), (
                f"{d} is not rooted under the custom data_dir"
            )


def test_crs_is_non_empty_string() -> None:
    assert isinstance(settings.crs, str) and settings.crs


def test_variables_info_all_two_tuples_of_str() -> None:
    for key, val in VARIABLES_INFO.items():
        assert isinstance(val, tuple) and len(val) == 2, (
            f"VARIABLES_INFO[{key!r}] must be a 2-tuple"
        )
        assert isinstance(val[0], str), f"VARIABLES_INFO[{key!r}][0] must be str"
        assert isinstance(val[1], str), f"VARIABLES_INFO[{key!r}][1] must be str"


def test_variables_pretty_derived_from_variables_info() -> None:
    assert VARIABLES_PRETTY == {k: v[0] for k, v in VARIABLES_INFO.items()}


def test_variables_inv_derived_from_variables_info() -> None:
    assert VARIABLES_INV == {v[0]: k for k, v in VARIABLES_INFO.items()}
