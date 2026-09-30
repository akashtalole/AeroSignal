"""Clean Air & Climate Resilience domain (Track 2) — a 6-agent ADK pipeline.

air_quality_monitor_agent and weather_context_agent run INDEPENDENTLY and
CONCURRENTLY as a ParallelAgent (both just need the corridor's lat/lng from
the initial request, neither depends on the other's output) — one genuine
fan-out over two real, live external data sources (Open-Meteo air quality
+ Open-Meteo weather). health_impact_agent then reads both branches'
state to score health risk. simulation_agent optionally projects a
"what-if" traffic/emissions intervention when the request includes a
scenario. Finally synthesis_agent and critic_agent run inside a LoopAgent:
synthesis_agent drafts the human-readable assessment, critic_agent checks
it for internal consistency (e.g. it must not say "safe" while AQI is in a
hazardous band) and either calls exit_loop when satisfied or explains what
to fix, which feeds back into the next synthesis_agent iteration.

Proactive escalation (drafting a public-health advisory when AQI crosses
a hazard threshold) is NOT an agent step — it is a plain deterministic
function, `maybe_draft_alert` in tools.py, run by main.py after this
pipeline finishes, so it always fires off the real numbers regardless of
what the LLM reasoning concluded.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.tools import exit_loop_tool

from tools import estimate_health_risk, fetch_air_quality, fetch_weather, simulate_intervention

MODEL = "gemini-flash-latest"

air_quality_monitor_agent = LlmAgent(
    name="air_quality_monitor",
    model=MODEL,
    description="Fetches live current + 48h air quality data for a corridor.",
    instruction=(
        "You monitor real-time air quality for a BRICS economic corridor "
        "analysis platform. The user's request names a corridor_id and its "
        "lat/lng coordinates. Call fetch_air_quality with that lat, lng, "
        "and corridor_id to get the REAL current PM2.5/PM10/NO2/ozone/"
        "carbon-monoxide/US-AQI readings and a 48h forecast. Report back "
        "the current US AQI and its category band, and the 48h max AQI, "
        "citing the actual numbers. If data_source is 'cached_baseline', "
        "say so explicitly (the live feed was unavailable and this used "
        "the corridor's cached baseline instead)."
    ),
    tools=[fetch_air_quality],
    output_key="air_quality_result",
)

weather_context_agent = LlmAgent(
    name="weather_context",
    model=MODEL,
    description="Fetches live wind/precipitation data and assesses pollution dispersion vs. trapping.",
    instruction=(
        "You assess meteorological context for a BRICS economic corridor "
        "air-quality platform. The user's request names a corridor_id and "
        "its lat/lng coordinates. Call fetch_weather with that lat, lng, "
        "and corridor_id to get REAL current wind speed/direction, "
        "precipitation, and temperature. Report back the wind speed/"
        "direction and whether conditions currently favor pollution "
        "DISPERSION or TRAPPING (per dispersion_condition/dispersion_note "
        "in the tool output), citing the actual numbers. If data_source is "
        "'cached_baseline', say so explicitly."
    ),
    tools=[fetch_weather],
    output_key="weather_result",
)

health_impact_agent = LlmAgent(
    name="health_impact_analyst",
    model=MODEL,
    description="Scores health risk by combining current AQI with nearby sensitive sites.",
    instruction=(
        "Air quality reading: {air_quality_result}\n\n"
        "Weather context: {weather_result}\n\n"
        "The user's original request also gave the corridor's "
        "sensitive_sites_estimate (nearby schools, hospitals, and eldercare "
        "facilities). Call estimate_health_risk with the current US AQI "
        "from the air quality reading above and that sensitive_sites_"
        "estimate to get a deterministic 1-5 risk_score and the most-"
        "exposed population groups. Explain the score in plain language, "
        "citing the actual risk_score, risk_label, and most_exposed_groups, "
        "and note whether trapping weather conditions make the near-term "
        "outlook worse."
    ),
    tools=[estimate_health_risk],
    output_key="health_risk_result",
)

simulation_agent = LlmAgent(
    name="intervention_simulator",
    model=MODEL,
    description="Projects the AQI impact of a what-if traffic/emissions intervention, when one was requested.",
    instruction=(
        "Air quality reading: {air_quality_result}\n\n"
        "The user's original request may include a 'scenario' with "
        "heavy_vehicle_reduction_pct, restricted_hours, and "
        "green_corridor_km levers for a what-if intervention.\n\n"
        "If a scenario WAS given: call simulate_intervention with the "
        "corridor_id, the current US AQI as baseline_aqi, and the "
        "scenario's three lever values. Report the projected_aqi, "
        "delta_aqi, and percent_change, citing the actual numbers, and "
        "note this is an illustrative heuristic, not a physics model.\n\n"
        "If NO scenario was given: do not call the tool. Simply state "
        "that no what-if scenario was requested, so this is a read-only "
        "analysis with no intervention simulated."
    ),
    tools=[simulate_intervention],
    output_key="simulation_result",
)

synthesis_agent = LlmAgent(
    name="synthesis_agent",
    model=MODEL,
    description="Drafts the final human-readable air-quality and health-risk assessment.",
    instruction=(
        "Air quality reading: {air_quality_result}\n\n"
        "Weather context: {weather_result}\n\n"
        "Health risk assessment: {health_risk_result}\n\n"
        "Intervention simulation: {simulation_result}\n\n"
        "Revision feedback from a previous review (if any, otherwise this "
        "is your first draft): {critic_feedback}\n\n"
        "Write a concise, plain-language final assessment for this "
        "corridor covering: (1) current AQI status and category band, "
        "citing the actual AQI number, (2) whether weather favors "
        "dispersion or trapping, (3) the health risk score and which "
        "population groups are most exposed, (4) if an intervention "
        "scenario was simulated, rank it by projected AQI impact and state "
        "the concrete before/after numbers — otherwise note none was "
        "requested. If revision feedback was given above, correct exactly "
        "what it flagged. Ground every claim in the actual numbers from "
        "the state above — never say a corridor is 'safe' if the AQI is in "
        "an Unhealthy or worse band."
    ),
    output_key="synthesis_result",
)

critic_agent = LlmAgent(
    name="critic_agent",
    model=MODEL,
    description="Checks the synthesis for internal consistency before it ships.",
    instruction=(
        "Review this draft assessment for internal consistency: "
        "{synthesis_result}\n\n"
        "Against the underlying data — air quality: {air_quality_result}; "
        "health risk: {health_risk_result} — check specifically that: "
        "(1) it never claims conditions are 'safe' or 'fine' while the AQI "
        "band is 'Unhealthy for Sensitive Groups' or worse, (2) the health "
        "risk score and exposed groups it cites match {health_risk_result} "
        "exactly, (3) any intervention numbers it cites match "
        "{simulation_result} exactly, (4) it is complete (covers AQI, "
        "weather, health risk, and the intervention status).\n\n"
        "If the draft is internally consistent and complete, call the "
        "exit_loop tool and say so — do not describe problems that do not "
        "exist. If it has a real inconsistency or omission, do NOT call "
        "exit_loop; instead explain concisely and specifically what must "
        "be fixed so the next draft can correct it."
    ),
    tools=[exit_loop_tool.exit_loop],
    output_key="critic_feedback",
)

review_loop = LoopAgent(
    name="synthesis_review_loop",
    sub_agents=[synthesis_agent, critic_agent],
    max_iterations=2,
)

clean_air_climate_agent = SequentialAgent(
    name="clean_air_climate_pipeline",
    description=(
        "Clean Air & Climate Resilience: fetches REAL live air-quality and "
        "weather data for a BRICS economic corridor, scores public-health "
        "risk, optionally simulates a what-if traffic/emissions "
        "intervention, and synthesizes a reviewed, internally-consistent "
        "assessment. Route here for anything about air quality, AQI, "
        "PM2.5, smog, pollution, weather-driven dispersion/trapping, "
        "health risk from air pollution, or what-if intervention "
        "simulation across BRICS economic corridors."
    ),
    sub_agents=[
        ParallelAgent(
            name="clean_air_data_collection",
            description="Fetches live air quality and weather data concurrently, independently.",
            sub_agents=[air_quality_monitor_agent, weather_context_agent],
        ),
        health_impact_agent,
        simulation_agent,
        review_loop,
    ],
)
