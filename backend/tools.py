"""Tools for the Clean Air & Climate Resilience multi-agent pipeline (Track 2).

Plain Python functions become ADK tools automatically when passed in an
LlmAgent's `tools=[...]` list — the docstring and type hints are used by
the model to understand what each tool does and how to call it. The same
functions are also called directly (as plain Python, no LLM involved) by
`main.py` in "offline" mode when no GEMINI_API_KEY is configured, so every
function here does real work on its own and never depends on an LLM having
already run.

MOCK DATA NOTE: `corridors.json`'s `baseline_aqi`, `wind_direction_deg`,
`wind_speed_kmh`, `humidity`, and `cross_border_neighbor_ids` are the same
illustrative BRICS-corridor reference data used elsewhere in this repo's
`adk-multi-agent-system/` prototype, used here only as a *fallback* when
the live Open-Meteo calls below fail. `sensitive_sites_estimate` (schools +
hospitals + eldercare facilities near each corridor) is hand-authored mock
data standing in for a real facility-registry / GIS layer — there is no
live facilities API wired in here. Everything else this module fetches
(current + 48h PM2.5/AQI, current wind/precipitation) is REAL, live data
from Open-Meteo's free, keyless APIs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from data_store import load_json

_DATA_DIR = Path(__file__).parent / "data"
CORRIDORS: list[dict[str, Any]] = load_json(_DATA_DIR / "corridors.json")
_CORRIDORS_BY_ID = {c["id"]: c for c in CORRIDORS}

_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_S = 8.0

# US AQI bands (https://www.airnow.gov), used consistently across this module.
_AQI_BANDS = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for Sensitive Groups"),
    (200, "Unhealthy"),
    (300, "Very Unhealthy"),
    (float("inf"), "Hazardous"),
]

HAZARD_AQI_THRESHOLD = 150  # crossing this auto-drafts a proactive advisory


def get_corridor(corridor_id: str) -> dict[str, Any] | None:
    """Plain internal lookup, not an agent tool."""
    return _CORRIDORS_BY_ID.get(corridor_id)


def list_corridors() -> dict[str, Any]:
    """Lists every BRICS economic corridor/city tracked by this platform,
    with its id, country, corridor name, coordinates, baseline AQI, and
    estimated count of nearby sensitive sites (schools, hospitals, eldercare
    facilities)."""
    return {"status": "success", "corridors": CORRIDORS}


def aqi_band(aqi: float) -> str:
    """Plain internal helper mapping a US AQI value to its category label."""
    for ceiling, label in _AQI_BANDS:
        if aqi <= ceiling:
            return label
    return "Hazardous"


async def fetch_air_quality(lat: float, lng: float, corridor_id: str) -> dict[str, Any]:
    """Fetches REAL current + 48h air quality data for a location from the
    Open-Meteo Air Quality API (free, no API key): current PM2.5, PM10,
    NO2, ozone, carbon monoxide, and US AQI, plus an hourly PM2.5/US AQI
    series for the next 48 hours.

    If the live call fails or times out (8s), falls back to the corridor's
    static baseline_aqi from corridors.json and marks the response
    data_source="cached_baseline" instead of "live" — this never hard-fails
    just because an external API hiccuped.

    Args:
        lat: latitude of the corridor.
        lng: longitude of the corridor.
        corridor_id: id of the corridor (used only for the fallback lookup
            if the live call fails — see list_corridors).
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "pm2_5,pm10,nitrogen_dioxide,ozone,carbon_monoxide,us_aqi",
        "hourly": "pm2_5,us_aqi",
        "forecast_days": 2,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(_AIR_QUALITY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        current = data["current"]
        hourly = data["hourly"]
        forecast_48h = [
            {"time": t, "pm2_5": pm, "us_aqi": aqi}
            for t, pm, aqi in zip(hourly["time"], hourly["pm2_5"], hourly["us_aqi"])
        ]
        aqi_48h_max = max((f["us_aqi"] for f in forecast_48h), default=current["us_aqi"])
        return {
            "status": "success",
            "data_source": "live",
            "corridor_id": corridor_id,
            "current": {
                "time": current["time"],
                "pm2_5": current["pm2_5"],
                "pm10": current["pm10"],
                "nitrogen_dioxide": current["nitrogen_dioxide"],
                "ozone": current["ozone"],
                "carbon_monoxide": current["carbon_monoxide"],
                "us_aqi": current["us_aqi"],
            },
            "aqi_band": aqi_band(current["us_aqi"]),
            "forecast_48h": forecast_48h,
            "aqi_48h_max": aqi_48h_max,
        }
    except Exception as exc:  # noqa: BLE001 - deliberately broad, this must never hard-fail
        corridor = get_corridor(corridor_id) or {}
        baseline_aqi = corridor.get("baseline_aqi", 100)
        return {
            "status": "success",
            "data_source": "cached_baseline",
            "data_source_note": f"live Open-Meteo air-quality call failed ({exc.__class__.__name__}); using corridor baseline",
            "corridor_id": corridor_id,
            "current": {
                "time": None,
                "pm2_5": None,
                "pm10": None,
                "nitrogen_dioxide": None,
                "ozone": None,
                "carbon_monoxide": None,
                "us_aqi": baseline_aqi,
            },
            "aqi_band": aqi_band(baseline_aqi),
            "forecast_48h": [],
            "aqi_48h_max": baseline_aqi,
        }


async def fetch_weather(lat: float, lng: float, corridor_id: str) -> dict[str, Any]:
    """Fetches REAL current weather/wind data for a location from the
    Open-Meteo Forecast API (free, no API key): wind speed, wind direction,
    precipitation, and temperature. Also assesses whether current
    conditions favor pollution DISPERSION (steady/strong wind, low
    humidity-proxy) or TRAPPING (low wind + rain/still air), a simple rule
    of thumb (wind_speed_10m < 8 km/h => trapping-prone).

    Falls back to the corridor's static wind_speed_kmh/wind_direction_deg
    from corridors.json (marking data_source="cached_baseline") if the live
    call fails or times out (8s) — never hard-fails the request.

    Args:
        lat: latitude of the corridor.
        lng: longitude of the corridor.
        corridor_id: id of the corridor (used only for the fallback lookup
            if the live call fails — see list_corridors).
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "wind_speed_10m,wind_direction_10m,precipitation,temperature_2m",
        "forecast_days": 2,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(_WEATHER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        current = data["current"]
        wind_speed = current["wind_speed_10m"]
        dispersion = "trapping" if wind_speed < 8 else "dispersing"
        return {
            "status": "success",
            "data_source": "live",
            "corridor_id": corridor_id,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": current["wind_direction_10m"],
            "precipitation_mm": current["precipitation"],
            "temperature_c": current["temperature_2m"],
            "dispersion_condition": dispersion,
            "dispersion_note": (
                "Low wind speed favors pollution TRAPPING near ground level."
                if dispersion == "trapping"
                else "Wind speed favors pollution DISPERSION away from the source."
            ),
        }
    except Exception as exc:  # noqa: BLE001 - deliberately broad, this must never hard-fail
        corridor = get_corridor(corridor_id) or {}
        wind_speed = corridor.get("wind_speed_kmh", 15)
        dispersion = "trapping" if wind_speed < 8 else "dispersing"
        return {
            "status": "success",
            "data_source": "cached_baseline",
            "data_source_note": f"live Open-Meteo weather call failed ({exc.__class__.__name__}); using corridor baseline",
            "corridor_id": corridor_id,
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": corridor.get("wind_direction_deg", 180),
            "precipitation_mm": 0.0,
            "temperature_c": None,
            "dispersion_condition": dispersion,
            "dispersion_note": (
                "Low wind speed favors pollution TRAPPING near ground level."
                if dispersion == "trapping"
                else "Wind speed favors pollution DISPERSION away from the source."
            ),
        }


def estimate_health_risk(aqi: float, sensitive_sites_estimate: int) -> dict[str, Any]:
    """Deterministically combines the current US AQI band with a corridor's
    estimated count of nearby sensitive sites (schools, hospitals, eldercare
    facilities) into a 1-5 health-risk score and the population groups most
    exposed. Not an LLM call — a fixed rule table, so the score is always
    reproducible for the same inputs.

    Args:
        aqi: current US AQI value.
        sensitive_sites_estimate: mock count of nearby schools/hospitals/
            eldercare facilities for this corridor (see corridors.json).
    """
    if aqi <= 50:
        base_score = 1
    elif aqi <= 100:
        base_score = 2
    elif aqi <= 150:
        base_score = 3
    elif aqi <= 200:
        base_score = 4
    else:
        base_score = 5

    # A high concentration of sensitive sites bumps an already-elevated
    # score by up to +1 (capped at 5) — same AQI is a bigger public-health
    # problem where more schools/hospitals/eldercare facilities sit nearby.
    bump = 1 if (sensitive_sites_estimate >= 45 and base_score >= 3) else 0
    risk_score = min(5, base_score + bump)

    if risk_score <= 1:
        exposed_groups = ["general population (low risk at this level)"]
    elif risk_score == 2:
        exposed_groups = ["people with asthma or respiratory sensitivity"]
    elif risk_score == 3:
        exposed_groups = ["children", "elderly residents", "people with respiratory/cardiac conditions"]
    elif risk_score == 4:
        exposed_groups = ["children", "elderly residents", "outdoor workers", "anyone with respiratory or cardiac conditions"]
    else:
        exposed_groups = ["entire general population", "children", "elderly residents", "outdoor workers", "anyone with a pre-existing condition"]

    return {
        "status": "success",
        "aqi": aqi,
        "aqi_band": aqi_band(aqi),
        "sensitive_sites_estimate": sensitive_sites_estimate,
        "risk_score": risk_score,
        "risk_label": ["", "Minimal", "Low", "Moderate", "High", "Severe"][risk_score],
        "most_exposed_groups": exposed_groups,
    }


def simulate_intervention(
    corridor_id: str,
    baseline_aqi: float,
    heavy_vehicle_reduction_pct: float = 0,
    restricted_hours: float = 0,
    green_corridor_km: float = 0,
) -> dict[str, Any]:
    """Simulates the projected AQI impact of a "what-if" traffic/emissions
    intervention on a corridor.

    This is a DELIBERATELY SIMPLE, illustrative heuristic, not a real
    atmospheric-dispersion or emissions-inventory model (no CFD/box model
    in this prototype): each lever contributes a fixed linear discount off
    the baseline AQI —

        projected_aqi = baseline_aqi * (
            1
            - 0.004 * heavy_vehicle_reduction_pct   (0-100, % heavy-vehicle traffic cut)
            - 0.006 * restricted_hours               (0-24, hours/day of traffic restriction)
            - 0.01  * green_corridor_km               (0-10, km of new green-corridor/buffer)
        )

    clamped with a floor of max(baseline_aqi * 0.35, ...) so the model can
    never claim an unrealistic >65% cut from these levers alone, regardless
    of how aggressive the inputs are.

    Args:
        corridor_id: id of the corridor being simulated.
        baseline_aqi: the corridor's current/baseline AQI to project from.
        heavy_vehicle_reduction_pct: 0-100, percent reduction in heavy
            vehicle traffic.
        restricted_hours: 0-24, hours per day of traffic restriction.
        green_corridor_km: 0-10, kilometers of new green corridor/buffer
            planting.
    """
    discount = (
        0.004 * heavy_vehicle_reduction_pct
        + 0.006 * restricted_hours
        + 0.01 * green_corridor_km
    )
    raw_projected = baseline_aqi * (1 - discount)
    floor = baseline_aqi * 0.35
    projected_aqi = max(floor, raw_projected)
    delta = projected_aqi - baseline_aqi

    return {
        "status": "success",
        "corridor_id": corridor_id,
        "baseline_aqi": round(baseline_aqi, 1),
        "scenario": {
            "heavy_vehicle_reduction_pct": heavy_vehicle_reduction_pct,
            "restricted_hours": restricted_hours,
            "green_corridor_km": green_corridor_km,
        },
        "projected_aqi": round(projected_aqi, 1),
        "delta_aqi": round(delta, 1),
        "percent_change": round((delta / baseline_aqi) * 100, 1) if baseline_aqi else 0.0,
        "projected_aqi_band": aqi_band(projected_aqi),
        "note": (
            "Illustrative linear heuristic for demo purposes, not a real "
            "atmospheric dispersion or emissions-inventory model."
        ),
    }


def maybe_draft_alert(aqi_now: float, aqi_48h_max: float, corridor_id: str) -> dict[str, Any] | None:
    """Proactively drafts a short public-health advisory when AQI crosses
    the hazard threshold (US AQI > 150 = "Unhealthy for Sensitive Groups"
    or worse) — either right now or forecast to within the next 48h. This
    is a plain deterministic function (not an LLM agent) that fires
    automatically off the numbers; it is called by main.py after the
    analysis pipeline finishes, whether or not the caller asked for an
    alert.

    Returns None when neither the current nor forecast AQI crosses the
    threshold (no advisory drafted).

    Args:
        aqi_now: current US AQI.
        aqi_48h_max: the maximum forecast US AQI over the next 48h.
        corridor_id: id of the corridor this advisory concerns.
    """
    worst_aqi = max(aqi_now, aqi_48h_max)
    if worst_aqi <= HAZARD_AQI_THRESHOLD:
        return None

    corridor = get_corridor(corridor_id) or {}
    country = corridor.get("country", "the region")
    corridor_name = corridor.get("corridor", corridor_id)

    if worst_aqi > 300:
        level = "severe"
    elif worst_aqi > 200:
        level = "high"
    else:
        level = "moderate"

    driver = "current conditions" if aqi_now > HAZARD_AQI_THRESHOLD else "the 48h forecast"
    neighbors = corridor.get("cross_border_neighbor_ids", [])
    neighbor_note = (
        f" Cross-border neighbors ({', '.join(neighbors)}) should be notified for coordinated response."
        if neighbors
        else ""
    )

    message = (
        f"AIR QUALITY ADVISORY — {level.upper()} — {corridor_name}, {country}. "
        f"US AQI has crossed the hazard threshold ({HAZARD_AQI_THRESHOLD}), driven by {driver} "
        f"(current={round(aqi_now)}, 48h max={round(aqi_48h_max)}, category: {aqi_band(worst_aqi)}). "
        f"Recommended authority: {country} national/municipal environmental & public health agency for "
        f"{corridor_name}. Sensitive groups (children, elderly, respiratory/cardiac conditions) should "
        f"limit prolonged outdoor exposure until levels subside.{neighbor_note}"
    )

    return {
        "level": level,
        "corridor_id": corridor_id,
        "corridor": corridor_name,
        "country": country,
        "authority": f"{country} national/municipal environmental & public health agency",
        "aqi_now": round(aqi_now),
        "aqi_48h_max": round(aqi_48h_max),
        "threshold": HAZARD_AQI_THRESHOLD,
        "driver": driver,
        "affected_neighbors": neighbors,
        "message": message,
    }
