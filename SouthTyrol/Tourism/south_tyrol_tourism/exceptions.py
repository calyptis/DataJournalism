class TourismError(Exception):
    """Base exception for all south_tyrol_tourism errors."""


class APIError(TourismError):
    """Raised when an API request fails or returns unexpected data."""


class DataError(TourismError):
    """Raised when data is missing, malformed, or fails a consistency check."""
