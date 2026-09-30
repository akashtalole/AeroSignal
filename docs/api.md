# API Reference

Base URL (local dev): `http://localhost:8788`

## `GET /api/corridors`

Returns the 17 tracked corridors (9 Indian states + 8 other BRICS corridors) with
lat/lng, baseline AQI, and metadata.

## `POST /api/analyze`

Runs the full pipeline synchronously for a corridor.

**Response:**

```json
{
  "mode": "gemini | offline",
  "data_source": "live | cached_baseline",
  "corridor": { "...": "..." },
  "air_quality": { "...": "..." },
  "weather": { "...": "..." },
  "health_risk": { "...": "..." },
  "simulation": { "...": "..." },
  "alert": { "...": "..." },
  "narrative": "string",
  "trace": [ { "agent": "string", "...": "..." } ]
}
```

## `GET /api/analyze/stream`

Same pipeline as `/api/analyze`, streamed as Server-Sent Events — one event per agent
step, carrying the pipeline's real ADK `Event` objects when running in `gemini` mode.

## `POST /api/translate`

Translates narrative/advisory text via Gemini. Returns an honest note (no fabricated
translation) when running in offline mode.

## `GET /api/corridors/{id}/satellite`

Optional Google Earth Engine imagery for a corridor.

**Response (available):**

```json
{
  "available": true,
  "tile_url_rgb": "https://...",
  "tile_url_ndvi": "https://...",
  "date_range": "2026-08-01 to 2026-09-30"
}
```

**Response (not configured):**

```json
{ "available": false, "reason": "string" }
```

Always returns `200`/`404` — never `500` — regardless of Earth Engine configuration
state.
