from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Runtime configuration.

    All path fields rooted under ``data_dir`` are derived automatically.
    Override ``data_dir`` (or ``plot_dir``) via the ``TOURISM_DATA_DIR`` /
    ``TOURISM_PLOT_DIR`` environment variables, e.g. for Docker mounts.
    """

    model_config = SettingsConfigDict(env_prefix="TOURISM_", frozen=True)

    # Overridable roots
    data_dir: Path = _BASE_DIR / "data"
    plot_dir: Path = _BASE_DIR / "plots"
    crs: str = "EPSG:4326"

    # --- Directories ---

    @computed_field
    @property
    def raw_data_dir(self) -> Path:
        return self.data_dir / "raw_data"

    @computed_field
    @property
    def api_calls_dir(self) -> Path:
        return self.raw_data_dir / "api_calls"

    @computed_field
    @property
    def main_call_dir(self) -> Path:
        return self.api_calls_dir / "main_call"

    @computed_field
    @property
    def prepared_data_dir(self) -> Path:
        return self.data_dir / "prepared_data"

    @computed_field
    @property
    def dashboard_data_dir(self) -> Path:
        return self.data_dir / "dashboard_data"

    @computed_field
    @property
    def dirs(self) -> list[Path]:
        return [
            self.data_dir,
            self.plot_dir,
            self.raw_data_dir,
            self.prepared_data_dir,
            self.api_calls_dir,
            self.main_call_dir,
            self.dashboard_data_dir,
        ]

    # --- Raw input files ---

    @computed_field
    @property
    def population_shapefile(self) -> Path:
        return (
            self.raw_data_dir
            / "shapefiles"
            / "FME_14060355_1660760091426_63496"
            / "DownloadService"
            / "OfficialResidentPopulation_polygon.shp"
        )

    @computed_field
    @property
    def province_shapefile(self) -> Path:
        return (
            self.raw_data_dir
            / "shapefiles"
            / "Limiti01012021_g"
            / "ProvCM01012021_g"
            / "ProvCM01012021_g_WGS84.shp"
        )

    # --- Pipeline files ---

    @computed_field
    @property
    def raw_accommodation_file(self) -> Path:
        """Consolidated JSON written by download_data()."""
        return self.main_call_dir / "accommodations_raw.json"

    @computed_field
    @property
    def parsed_accommodation_file(self) -> Path:
        return self.prepared_data_dir / "accommodations_parsed.parquet"

    @computed_field
    @property
    def prepared_accommodation_file(self) -> Path:
        return self.dashboard_data_dir / "accommodations_cleaned.parquet"

    # --- Dashboard files ---

    @computed_field
    @property
    def municipality_file(self) -> Path:
        return self.dashboard_data_dir / "municipality.parquet"

    @computed_field
    @property
    def south_tyrol_boundary_file(self) -> Path:
        return self.dashboard_data_dir / "south_tyrol_boundary.parquet"


# Module-level singleton used throughout the package
settings = Settings()

# ---------------------------------------------------------------------------
# Domain constants — not environment-dependent, stay as plain dicts
# ---------------------------------------------------------------------------

VARIABLES_INFO: dict[str, tuple[str, str]] = {
    "nr_establishments": ("Number of Tourism Establishments", "{,}"),
    "nr_establishments_per_thousand_pop": (
        "Number of Tourism Establishments per 1,000 Inhabitants",
        "{,}",
    ),
    "NAME_D": ("Municipality (de)", ""),
    "NAME_I": ("Municipality (it)", ""),
    "share_1_rating": ("Share of Establishments with Rating 1", "{0.2f}%"),
    "share_2_rating": ("Share of Establishments with Rating 2", "{0.2f}%"),
    "share_3_rating": ("Share of Establishments with Rating 3", "{0.2f}%"),
    "share_3s_rating": ("Share of Establishments with Rating 3S", "{0.2f}%"),
    "share_4_rating": ("Share of Establishments with Rating 4", "{0.2f}%"),
    "share_4s_rating": ("Share of Establishments with Rating 4S", "{0.2f}%"),
    "share_5_rating": ("Share of Establishments with Rating 5", "{0.2f}%"),
    "share_hotels": ("Hotels %", "{0.1f}%"),
    "share_apartments": ("Apartments %", "{0.1f}%"),
    "share_farms": ("Farms %", "{0.1f}%"),
    "share_hotel_rating_1": ("Hotels — Rating 1 %", "{0.1f}%"),
    "share_hotel_rating_2": ("Hotels — Rating 2 %", "{0.1f}%"),
    "share_hotel_rating_3": ("Hotels — Rating 3 %", "{0.1f}%"),
    "share_hotel_rating_3s": ("Hotels — Rating 3S %", "{0.1f}%"),
    "share_hotel_rating_4": ("Hotels — Rating 4 %", "{0.1f}%"),
    "share_hotel_rating_4s": ("Hotels — Rating 4S %", "{0.1f}%"),
    "share_hotel_rating_5": ("Hotels — Rating 5 %", "{0.1f}%"),
    "share_apartment_rating_1": ("Apartments — Rating 1 %", "{0.1f}%"),
    "share_apartment_rating_2": ("Apartments — Rating 2 %", "{0.1f}%"),
    "share_apartment_rating_3": ("Apartments — Rating 3 %", "{0.1f}%"),
    "share_apartment_rating_3s": ("Apartments — Rating 3S %", "{0.1f}%"),
    "share_apartment_rating_4": ("Apartments — Rating 4 %", "{0.1f}%"),
    "share_apartment_rating_4s": ("Apartments — Rating 4S %", "{0.1f}%"),
    "share_apartment_rating_5": ("Apartments — Rating 5 %", "{0.1f}%"),
    "share_farm_rating_1": ("Farms — Rating 1 %", "{0.1f}%"),
    "share_farm_rating_2": ("Farms — Rating 2 %", "{0.1f}%"),
    "share_farm_rating_3": ("Farms — Rating 3 %", "{0.1f}%"),
    "share_farm_rating_3s": ("Farms — Rating 3S %", "{0.1f}%"),
    "share_farm_rating_4": ("Farms — Rating 4 %", "{0.1f}%"),
    "share_farm_rating_4s": ("Farms — Rating 4S %", "{0.1f}%"),
    "share_farm_rating_5": ("Farms — Rating 5 %", "{0.1f}%"),
}

VARIABLES_PRETTY: dict[str, str] = {k: v[0] for k, v in VARIABLES_INFO.items()}
VARIABLES_INV: dict[str, str] = {v[0]: k for k, v in VARIABLES_INFO.items()}

# Mapping to type of establishment as per
# https://www.suedtirol.de/klassifizierung-sterne-sonnen-blumen.html
MAPPING_CATEGORY: dict[str, str] = {
    "flower": "Farm",
    "star": "Hotel",
    "sun": "Apartment",
    "stars": "Hotel",
    "suns": "Apartment",
    "flowers": "Farm",
}
ACCOMMODATION_API = "https://tourism.api.opendatahub.bz.it/v1/Accommodation"
