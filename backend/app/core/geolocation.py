"""
TRACE - Geolocation Utilities
Haversine formula for geo-fence validation.
"""

import math

from app.config import get_settings

settings = get_settings()


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great-circle distance between two GPS points using
    the Haversine formula.

    Args:
        lat1, lon1: Coordinates of point 1 (employee location).
        lat2, lon2: Coordinates of point 2 (office/geo-fence center).

    Returns:
        Distance in meters.
    """
    R = 6_371_000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def check_geo_fence(
    employee_lat: float,
    employee_lon: float,
    office_lat: float,
    office_lon: float,
    radius_meters: float | None = None,
) -> str:
    """
    Determine attendance location status based on geo-fence.

    Returns:
        'office' if within radius, 'suspicious' if outside.
    """
    radius = radius_meters or settings.DEFAULT_GEO_FENCE_RADIUS_METERS
    distance = haversine_distance(employee_lat, employee_lon, office_lat, office_lon)

    if distance <= radius:
        return "office"
    return "suspicious"
