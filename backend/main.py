"""FastAPI app for the Clean Air & Climate Resilience platform (Track 2).

Custom REST endpoints (not the generic `get_fast_api_app` ADK dev server,
since the response shapes here are bespoke) plus a catch-all static-file
route that serves the built frontend, so the whole app runs as one Cloud
Run service exactly like the previous Node/Express version did.

Two modes, chosen automatically by whether Gemini is reachable — either via
GEMINI_API_KEY (Google AI Studio) or, when an org policy disallows API keys,
via Vertex AI + Application Default Credentials (GOOGLE_GENAI_USE_VERTEXAI=TRUE
plus GOOGLE_CLOUD_PROJECT/GOOGLE_CLOUD_LOCATION, using the Cloud Run service's
own service account identity — no key of any kind required):

- "gemini": runs the real ADK multi-agent pipeline (agent.py) via a
  Runner, streaming its actual Event objects for a genuinely live agent
  trace.
- "offline": no LLM available, so the ADK Runner/LlmAgent pipeline is
  skipped entirely and the same tool functions are called directly as
  plain Python — the fetched air-quality/weather numbers are still 100%
  real, only the LLM reasoning/narration layer is replaced by a
  deterministic template.

In both modes the structured response fields (air_quality, weather,
health_risk, simulation, alert) are always built from direct calls to the
tools in tools.py, so they are correct and fast regardless of what the LLM
pipeline itself does; in "gemini" mode the ADK pipeline additionally runs
end-to-end to produce a genuine `narrative` (from its synthesis_result
state) and a genuine agent-by-agent `trace` (from its real Event stream).
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse

from earth_engine import get_corridor_satellite
from tools import (
    CORRIDORS,
    estimate_health_risk,
    fetch_air_quality,
    fetch_weather,
    get_corridor,
    maybe_draft_alert,
    simulate_intervention,
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Vertex AI + ADC path: no key at all, just the Cloud Run service's own
# identity — the google-genai Client (used both by ADK's LlmAgent internally
# and by the /api/translate call below) auto-detects this from the same
# three env vars, falling back to google.auth.default() for credentials.
VERTEX_CONFIGURED = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in (
    "1",
    "true",
) and bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
MODE = "gemini" if (GEMINI_API_KEY or VERTEX_CONFIGURED) else "offline"

app = FastAPI(title="Clean Air & Climate Resilience API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API router is defined and mounted FIRST so it is never shadowed by the
# static-file catch-all registered further down. --------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "mode": MODE}


@app.get("/api/corridors")
async def list_corridors_endpoint() -> list[dict[str, Any]]:
    return [
        {
            "id": c["id"],
            "country": c["country"],
            "state": c.get("state"),
            "corridor": c["corridor"],
            "lat": c["lat"],
            "lng": c["lng"],
            "baseline_aqi": c["baseline_aqi"],
            "sensitive_sites_estimate": c["sensitive_sites_estimate"],
        }
        for c in CORRIDORS
    ]


def _corridor_or_404(corridor_id: str) -> dict[str, Any] | None:
    return get_corridor(corridor_id)


async def _fetch_structured(corridor: dict[str, Any], scenario: dict[str, Any] | None) -> dict[str, Any]:
    """Direct (non-LLM) calls to the real tools — the source of truth for
    every structured field in the response, in both offline and gemini
    mode."""
    aq_task = fetch_air_quality(corridor["lat"], corridor["lng"], corridor["id"])
    wx_task = fetch_weather(corridor["lat"], corridor["lng"], corridor["id"])
    air_quality, weather = await asyncio.gather(aq_task, wx_task)

    health_risk = estimate_health_risk(
        air_quality["current"]["us_aqi"], corridor["sensitive_sites_estimate"]
    )

    simulation = None
    if scenario:
        simulation = simulate_intervention(
            corridor_id=corridor["id"],
            baseline_aqi=air_quality["current"]["us_aqi"],
            heavy_vehicle_reduction_pct=scenario.get("heavy_vehicle_reduction_pct", 0),
            restricted_hours=scenario.get("restricted_hours", 0),
            green_corridor_km=scenario.get("green_corridor_km", 0),
        )

    alert = maybe_draft_alert(
        aqi_now=air_quality["current"]["us_aqi"],
        aqi_48h_max=air_quality["aqi_48h_max"],
        corridor_id=corridor["id"],
    )

    overall_data_source = (
        "live" if air_quality["data_source"] == "live" and weather["data_source"] == "live" else "cached_baseline"
    )

    return {
        "data_source": overall_data_source,
        "air_quality": air_quality,
        "weather": weather,
        "health_risk": health_risk,
        "simulation": simulation,
        "alert": alert,
    }


def _offline_trace(structured: dict[str, Any], scenario: dict[str, Any] | None) -> list[dict[str, str]]:
    aq = structured["air_quality"]
    wx = structured["weather"]
    hr = structured["health_risk"]
    trace = [
        {
            "agent": "air_quality_monitor",
            "summary": (
                f"Fetched {aq['data_source']} air quality: US AQI {aq['current']['us_aqi']} "
                f"({aq['aqi_band']}), PM2.5 {aq['current']['pm2_5']}."
            ),
        },
        {
            "agent": "weather_context",
            "summary": (
                f"Fetched {wx['data_source']} weather: wind {wx['wind_speed_kmh']} km/h "
                f"from {wx['wind_direction_deg']}° — conditions favor {wx['dispersion_condition']}."
            ),
        },
        {
            "agent": "health_impact_analyst",
            "summary": (
                f"Risk score {hr['risk_score']}/5 ({hr['risk_label']}); most exposed: "
                f"{', '.join(hr['most_exposed_groups'])}."
            ),
        },
    ]
    if scenario:
        sim = structured["simulation"]
        trace.append(
            {
                "agent": "intervention_simulator",
                "summary": (
                    f"Scenario projects AQI {sim['baseline_aqi']} -> {sim['projected_aqi']} "
                    f"({sim['percent_change']}%)."
                ),
            }
        )
    else:
        trace.append({"agent": "intervention_simulator", "summary": "No what-if scenario requested — skipped."})
    trace.append(
        {
            "agent": "synthesis_agent",
            "summary": "Assembled deterministic offline narrative from the above (no LLM key configured).",
        }
    )
    if structured["alert"]:
        trace.append(
            {
                "agent": "escalation",
                "summary": f"AQI crossed hazard threshold — drafted a {structured['alert']['level']} advisory.",
            }
        )
    return trace


def _offline_narrative(corridor: dict[str, Any], structured: dict[str, Any], scenario: dict[str, Any] | None) -> str:
    aq = structured["air_quality"]
    wx = structured["weather"]
    hr = structured["health_risk"]
    lines = [
        f"{corridor['corridor']}, {corridor['country']}: current US AQI is {aq['current']['us_aqi']} "
        f"({aq['aqi_band']}), 48h max forecast {aq['aqi_48h_max']}.",
        f"Wind is {wx['wind_speed_kmh']} km/h from {wx['wind_direction_deg']}° — conditions favor "
        f"{wx['dispersion_condition']} ({wx['dispersion_note']}).",
        f"Health risk score: {hr['risk_score']}/5 ({hr['risk_label']}), with an estimated "
        f"{corridor['sensitive_sites_estimate']} sensitive sites nearby. Most exposed: "
        f"{', '.join(hr['most_exposed_groups'])}.",
    ]
    if scenario and structured["simulation"]:
        sim = structured["simulation"]
        lines.append(
            f"What-if simulation: cutting heavy-vehicle traffic {sim['scenario']['heavy_vehicle_reduction_pct']}%, "
            f"restricting traffic {sim['scenario']['restricted_hours']}h/day, and adding "
            f"{sim['scenario']['green_corridor_km']}km of green corridor projects AQI moving from "
            f"{sim['baseline_aqi']} to {sim['projected_aqi']} ({sim['percent_change']}%)."
        )
    else:
        lines.append("No what-if intervention scenario was requested for this analysis.")
    if structured["alert"]:
        lines.append(f"PROACTIVE ALERT: {structured['alert']['message']}")
    else:
        lines.append("No active alert — AQI is within the hazard threshold.")
    return " ".join(lines)


def _build_prompt(corridor: dict[str, Any], scenario: dict[str, Any] | None) -> str:
    scenario_text = (
        f"Scenario requested — simulate: heavy_vehicle_reduction_pct={scenario.get('heavy_vehicle_reduction_pct', 0)}, "
        f"restricted_hours={scenario.get('restricted_hours', 0)}, green_corridor_km={scenario.get('green_corridor_km', 0)}."
        if scenario
        else "No what-if scenario requested — this is a read-only analysis."
    )
    return (
        f"Analyze corridor_id={corridor['id']} ({corridor['corridor']}, {corridor['country']}) "
        f"at lat={corridor['lat']}, lng={corridor['lng']}. Baseline AQI={corridor['baseline_aqi']}. "
        f"sensitive_sites_estimate={corridor['sensitive_sites_estimate']}. "
        f"cross_border_neighbor_ids={corridor.get('cross_border_neighbor_ids', [])}. "
        f"{scenario_text} Run the full monitoring, health-risk, simulation, and synthesis pipeline."
    )


async def _run_gemini_pipeline(corridor: dict[str, Any], scenario: dict[str, Any] | None):
    """Runs the real ADK Runner pipeline, yielding (event_dict, None) for
    each Event as it streams, then finally (None, narrative) once the run
    completes and session state can be read."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from agent import clean_air_climate_agent

    session_service = InMemorySessionService()
    user_id = "demo-user"
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name="clean_air_climate", user_id=user_id, session_id=session_id
    )
    runner = Runner(
        agent=clean_air_climate_agent, app_name="clean_air_climate", session_service=session_service
    )
    prompt = _build_prompt(corridor, scenario)

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        text = ""
        if event.content and event.content.parts:
            text = " ".join(p.text for p in event.content.parts if getattr(p, "text", None))
        yield (
            {
                "agent": event.author,
                "type": "final" if event.is_final_response() else "step",
                "summary": (text[:400] if text else f"{event.author} step"),
            },
            None,
        )

    session = await session_service.get_session(
        app_name="clean_air_climate", user_id=user_id, session_id=session_id
    )
    narrative = (session.state.get("synthesis_result") if session else None) or None
    yield (None, narrative)


@app.post("/api/analyze")
async def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    corridor_id = payload.get("corridor_id")
    scenario = payload.get("scenario")
    corridor = _corridor_or_404(corridor_id) if corridor_id else None
    if not corridor:
        return JSONResponse(status_code=404, content={"error": f"unknown corridor_id '{corridor_id}'"})

    structured = await _fetch_structured(corridor, scenario)

    response_mode = MODE
    if MODE == "offline":
        narrative = _offline_narrative(corridor, structured, scenario)
        trace = _offline_trace(structured, scenario)
    else:
        trace = []
        narrative = None
        try:
            async for event_dict, final_narrative in _run_gemini_pipeline(corridor, scenario):
                if event_dict:
                    trace.append({"agent": event_dict["agent"], "summary": event_dict["summary"]})
                if final_narrative:
                    narrative = final_narrative
        except Exception:  # noqa: BLE001 - Vertex/ADC or Gemini API can fail
            # (IAM grant still propagating, no ADC in this environment, quota,
            # network...) — never hard-fail the request over it, fall back to
            # the same real-data offline path everything else already uses.
            narrative = None
            trace = []
        if not narrative:
            # Safety net: either the LLM pipeline didn't produce a
            # synthesis_result, or it errored above — never ship an empty
            # narrative, and be honest in the response about which path ran.
            response_mode = "offline"
            narrative = _offline_narrative(corridor, structured, scenario)
            trace = _offline_trace(structured, scenario)

    return {
        "mode": response_mode,
        "data_source": structured["data_source"],
        "corridor": {
            "id": corridor["id"],
            "country": corridor["country"],
            "corridor": corridor["corridor"],
            "lat": corridor["lat"],
            "lng": corridor["lng"],
        },
        "air_quality": {
            "current": structured["air_quality"]["current"],
            "aqi_band": structured["air_quality"]["aqi_band"],
            "forecast_48h": structured["air_quality"]["forecast_48h"],
            "aqi_48h_max": structured["air_quality"]["aqi_48h_max"],
        },
        "weather": {
            k: v
            for k, v in structured["weather"].items()
            if k not in ("status",)
        },
        "health_risk": structured["health_risk"],
        "simulation": structured["simulation"],
        "alert": structured["alert"],
        "narrative": narrative,
        "trace": trace,
    }


@app.get("/api/corridors/{corridor_id}/satellite")
async def corridor_satellite(corridor_id: str) -> dict[str, Any]:
    """Optional Google Earth Engine upgrade: real Sentinel-2 true-color +
    NDVI tile URLs over the corridor's bounding box, when this deployment
    has Earth Engine available (see earth_engine.py). Always returns 200
    with either {"available": true, tile_url_rgb, tile_url_ndvi,
    date_range} or an honest {"available": false, "reason": "..."} —
    never a 500, so the frontend can always render something sensible."""
    corridor = _corridor_or_404(corridor_id)
    if not corridor:
        return JSONResponse(status_code=404, content={"error": f"unknown corridor_id '{corridor_id}'"})
    return get_corridor_satellite(corridor["lat"], corridor["lng"])


_LANGUAGE_NAMES = {"hi": "Hindi", "ta": "Tamil"}


@app.post("/api/translate")
async def translate(payload: dict[str, Any]) -> dict[str, Any]:
    """Translates a narrative/advisory string for the language toggle in the
    UI. Only meaningful in gemini mode (there is no offline translation
    model in this prototype) — in offline mode it returns the original
    text untranslated with a note explaining why, rather than faking a
    translation."""
    text = (payload.get("text") or "").strip()
    target_lang = payload.get("target_lang", "hi")
    lang_name = _LANGUAGE_NAMES.get(target_lang, target_lang)

    if MODE == "offline" or not text:
        return {
            "mode": "offline",
            "translated_text": None,
            "note": (
                "Translation requires GEMINI_API_KEY or Vertex AI "
                "(GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT) to be "
                "configured — showing English."
            ),
        }

    try:
        from google import genai

        # No api_key= when using Vertex/ADC — genai.Client() then auto-detects
        # GOOGLE_GENAI_USE_VERTEXAI/GOOGLE_CLOUD_PROJECT/GOOGLE_CLOUD_LOCATION
        # and falls back to Application Default Credentials, same as the ADK
        # Runner pipeline above does implicitly.
        client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()
        resp = client.models.generate_content(
            model="gemini-flash-latest",
            contents=(
                f"Translate the following air-quality advisory text into {lang_name}. "
                f"Output ONLY the translation, no preamble or quotes:\n\n{text}"
            ),
        )
        return {"mode": "gemini", "translated_text": (resp.text or "").strip(), "note": None}
    except Exception as exc:  # noqa: BLE001 - never hard-fail the UI over a translation hiccup
        return {"mode": "gemini", "translated_text": None, "note": f"translation failed: {exc.__class__.__name__}"}


@app.get("/api/analyze/stream")
async def analyze_stream(corridor_id: str, scenario: str | None = None):
    parsed_scenario = json.loads(scenario) if scenario else None
    corridor = _corridor_or_404(corridor_id)
    if not corridor:
        return JSONResponse(status_code=404, content={"error": f"unknown corridor_id '{corridor_id}'"})

    async def event_gen():
        structured = await _fetch_structured(corridor, parsed_scenario)

        stream_mode = MODE
        fall_back_to_offline = MODE == "offline"
        if not fall_back_to_offline:
            trace = []
            narrative = None
            try:
                async for event_dict, final_narrative in _run_gemini_pipeline(corridor, parsed_scenario):
                    if event_dict:
                        trace.append({"agent": event_dict["agent"], "summary": event_dict["summary"]})
                        yield f"data: {json.dumps(event_dict)}\n\n"
                    if final_narrative:
                        narrative = final_narrative
            except Exception:  # noqa: BLE001 - Vertex/ADC or Gemini API can fail mid-stream
                fall_back_to_offline = True
            if not narrative:
                fall_back_to_offline = True

        if fall_back_to_offline:
            stream_mode = "offline"
            trace = _offline_trace(structured, parsed_scenario)
            for step in trace:
                # Offline mode (or a live pipeline that errored/produced no
                # narrative) has no real streaming pipeline left to observe,
                # so this sleep is PURE UI PACING for the frontend's
                # live-trace animation — not simulated AI "thinking".
                yield f"data: {json.dumps({'agent': step['agent'], 'type': 'step', 'summary': step['summary']})}\n\n"
                await asyncio.sleep(0.4)
            narrative = _offline_narrative(corridor, structured, parsed_scenario)

        final_result = {
            "type": "final",
            "mode": stream_mode,
            "data_source": structured["data_source"],
            "corridor": {
                "id": corridor["id"],
                "country": corridor["country"],
                "corridor": corridor["corridor"],
                "lat": corridor["lat"],
                "lng": corridor["lng"],
            },
            "air_quality": {
                "current": structured["air_quality"]["current"],
                "aqi_band": structured["air_quality"]["aqi_band"],
                "forecast_48h": structured["air_quality"]["forecast_48h"],
                "aqi_48h_max": structured["air_quality"]["aqi_48h_max"],
            },
            "weather": {k: v for k, v in structured["weather"].items() if k not in ("status",)},
            "health_risk": structured["health_risk"],
            "simulation": structured["simulation"],
            "alert": structured["alert"],
            "narrative": narrative,
            "trace": trace,
        }
        yield f"data: {json.dumps(final_result)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# --- Static frontend, mounted AFTER the API routes above so it never
# shadows /api/* or /health. ------------------------------------------

_PUBLIC_DIR = Path(__file__).parent / "public"
if _PUBLIC_DIR.is_dir():
    if (_PUBLIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_PUBLIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        candidate = _PUBLIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_PUBLIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
