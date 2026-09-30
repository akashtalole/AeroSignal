"""Optional Google Earth Engine integration (Track 2) — real Sentinel-2
true-color + NDVI satellite imagery over a corridor's bounding box, when
(and only when) this process's environment gives Earth Engine something to
authenticate with.

Two manual, one-time steps only the deploying user can do (not this
codebase) are required before this ever turns itself on:
  1. Register the GCP project for Earth Engine access
     (https://code.earthengine.google.com -> Register a Noncommercial or
     Commercial Cloud project), and
  2. Grant the identity this process runs as (a Cloud Run service account,
     or a local `gcloud auth application-default login` user) the
     "Earth Engine Resource Viewer" (or broader) role on that project.

Verified against earthengine-api==1.7.46's actual source in this repo's
sandbox (not guessed):
  - `ee.Initialize(credentials='persistent', url=None, cloud_api_key=None,
    http_transport=None, project=None)` — when called with only `project=`
    and no explicit `credentials`, `ee.data.initialize()` (which it calls)
    never overrides `state.credentials` unless `credentials is not None`.
    The *first* ee.Initialize() call in a process is the one that matters
    here: `ee.Initialize(project=...)` with no credentials argument makes
    the underlying googleapiclient/google-auth machinery fall back to
    `google.auth.default()` — standard Application Default Credentials.
    On Cloud Run that's the attached service account; nothing has to be
    baked into this image or passed as a secret.
  - `ee.Image.getMapId(vis_params) -> dict[str, Any]` returns a dict whose
    `"tile_fetcher"` is an `ee.data.TileFetcher` object; its `.url_format`
    property (confirmed by reading ee/data.py) is a string of the form
    `<tile_base_url>/<version>/<map_name>/tiles/{z}/{x}/{y}` — the exact
    same `{z}/{x}/{y}` template syntax Leaflet's `L.tileLayer()` expects,
    so it can be handed to Leaflet unmodified.

Initialization is attempted at most ONCE per process, at import time. On
ANY failure (package present but no ADC, project not registered for Earth
Engine, wrong project, or simply no credentials available at all — the
case in this sandbox) `EE_AVAILABLE` is set False and Earth Engine is never
called again for that process's lifetime: a broken/unregistered project
won't start working on request #2 either, and retrying per-request would
add real latency to every single call for nothing.
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

logger = logging.getLogger("earth_engine")

EE_AVAILABLE = False
EE_INIT_ERROR: str | None = None

try:
    import ee
except Exception as exc:  # pragma: no cover - earthengine-api is a pinned requirement
    ee = None  # type: ignore[assignment]
    EE_INIT_ERROR = f"earthengine-api package not importable: {exc.__class__.__name__}: {exc}"
    logger.warning("Earth Engine unavailable: %s", EE_INIT_ERROR)

if ee is not None:
    _project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not _project:
        EE_INIT_ERROR = "GOOGLE_CLOUD_PROJECT is not set — Earth Engine needs a GCP project id to initialize"
        logger.info("Earth Engine not initialized: %s", EE_INIT_ERROR)
    else:
        try:
            ee.Initialize(project=_project)
            EE_AVAILABLE = True
            logger.info("Earth Engine initialized for project '%s'.", _project)
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure here means "no EE this process"
            EE_INIT_ERROR = (
                f"Earth Engine initialization failed for project '{_project}' "
                f"(is it registered for Earth Engine, and does its default service "
                f"account/ADC have Earth Engine access? see README.md): "
                f"{exc.__class__.__name__}: {exc}"
            )
            logger.warning("Earth Engine unavailable: %s", EE_INIT_ERROR)

_CLOUD_DAYS_LOOKBACK = 60
_MAX_CLOUD_PCT = 20
_RGB_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}
_NDVI_VIS = {
    "min": -0.2,
    "max": 0.8,
    "palette": ["#a50026", "#f46d43", "#fee08b", "#d9ef8b", "#66bd63", "#1a9850"],
}


def get_corridor_satellite(lat: float, lng: float, box_deg: float = 0.5) -> dict[str, Any]:
    """Builds a Sentinel-2 surface-reflectance true-color + NDVI tile URL
    pair over a corridor's bounding box (lat/lng +/- box_deg), from a
    cloud-filtered (<20% CLOUDY_PIXEL_PERCENTAGE) median composite over the
    last 60 days.

    Returns {"available": False, "reason": "<honest, specific reason>"}
    instead of raising whenever Earth Engine is not initialized for this
    process, or the Earth Engine call itself fails or finds no imagery —
    this function must never raise; main.py's endpoint turns its result
    directly into JSON, never a 500.
    """
    if not EE_AVAILABLE:
        return {"available": False, "reason": f"Earth Engine not initialized: {EE_INIT_ERROR}"}

    try:
        region = ee.Geometry.BBox(lng - box_deg, lat - box_deg, lng + box_deg, lat + box_deg)
        end = datetime.date.today()
        start = end - datetime.timedelta(days=_CLOUD_DAYS_LOOKBACK)
        date_range = f"{start.isoformat()} to {end.isoformat()}"

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start.isoformat(), end.isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", _MAX_CLOUD_PCT))
        )
        image_count = collection.size().getInfo()
        if not image_count:
            return {
                "available": False,
                "reason": (
                    f"no Sentinel-2 imagery found for this corridor with <{_MAX_CLOUD_PCT}% cloud "
                    f"cover in the last {_CLOUD_DAYS_LOOKBACK} days ({date_range})"
                ),
            }

        composite = collection.median().clip(region)

        rgb_map = composite.getMapId(_RGB_VIS)
        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndvi_map = ndvi.getMapId(_NDVI_VIS)

        return {
            "available": True,
            "tile_url_rgb": rgb_map["tile_fetcher"].url_format,
            "tile_url_ndvi": ndvi_map["tile_fetcher"].url_format,
            "date_range": date_range,
            "image_count": image_count,
        }
    except Exception as exc:  # noqa: BLE001 - never 500 the endpoint over an Earth Engine hiccup
        return {"available": False, "reason": f"Earth Engine request failed: {exc.__class__.__name__}: {exc}"}
