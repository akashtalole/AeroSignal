# AeroSignal

**Multi-agent AI for Clean Air & Climate Resilience — built for India, framed for BRICS**

> Submitted to **Code for Communities — Second Edition** (hack2skill, BRICS Agentic
> Platform) — Track 2: Clean Air & Climate Resilience.
>
> :material-rocket-launch: [Live demo](https://track2-clean-air-climate-719250423519.us-central1.run.app/) ·
> :material-source-repository: [Source on GitHub](https://github.com/akashtalole/aerosignal)

AeroSignal is a multi-agent AI platform for clean air and climate resilience, built for
India — scaling across 9 Indian states — and framed as a BRICS-wide system for
cross-border coordination. A Python [Google ADK](https://github.com/google/adk-python)
agent pipeline fetches real, live air-quality and weather data, scores public-health
risk, lets an authority simulate a traffic/emissions intervention before committing to
it, and proactively drafts a public-health advisory the moment air quality crosses a
hazard threshold — without anyone having to ask for one.

## The problem

> Major BRICS cities monitor macro-level air quality but consistently miss hyper-local
> and cross-border pollution events — industrial emissions, large-scale agricultural
> burning, trans-boundary smog. The absence of real-time, granular data and of tools to
> evaluate an intervention *before* deploying it prevents coordinated, evidence-based
> climate action.

The Lancet's India State-Level Disease Burden study attributes **1.67 million deaths a
year in India** to air pollution.

## What it does

1. **A genuine multi-agent ADK pipeline**, not a single classifier call —
   `air_quality_monitor` and `weather_context` fan out as a `ParallelAgent`,
   `health_impact_analyst` scores risk, `intervention_simulator` projects what-if
   scenarios, and `synthesis_agent` + `critic_agent` run inside a `LoopAgent` so the
   final assessment self-reviews for internal consistency (e.g. it can never say "safe"
   while the AQI is hazardous) before it ships.
2. **Real external data, with graceful fallback.** Every analysis calls Open-Meteo's
   free, keyless Air Quality API (current + 48h PM2.5/PM10/NO2/O3/CO/US AQI) and Weather
   API live. If a call fails or times out (8s), the response falls back to that
   corridor's static baseline and is honestly marked `data_source: "cached_baseline"`
   instead of `"live"` — it never hard-fails on an external API hiccup.
3. **Visible, not a black box.** `GET /api/analyze/stream` streams the pipeline's real
   ADK `Event` objects over Server-Sent Events as they happen, and the frontend's Agent
   Trace panel renders each step live.
4. **What-if intervention simulation.** Three sliders — heavy-vehicle traffic reduction
   %, traffic-restricted hours/day, new green-corridor km — re-run the analysis and show
   a clear baseline-vs-projected AQI comparison.
5. **Proactive escalation.** Whenever current or 48h-forecast US AQI crosses 150 (hazard
   threshold), the system automatically drafts a short public-health advisory naming the
   responsible authority and any neighboring corridors to notify.
6. **Built for India, scaling across states.** 9 of 17 tracked corridors are Indian —
   Delhi, Maharashtra, Karnataka, West Bengal, Tamil Nadu, Gujarat, Telangana, Uttar
   Pradesh, and Bihar — alongside 8 other BRICS corridors (China, Brazil, Russia, South
   Africa, Egypt) for cross-border framing.
7. **Multilingual & voice support.** Assessments and advisories can be read aloud via the
   browser's native `SpeechSynthesis` API (no key required) and toggled between English,
   Hindi, and Tamil.
8. **Two optional Google Geo upgrades, both off by default.** A real Google Maps map and
   real Google Earth Engine Sentinel-2/NDVI satellite imagery over a selected corridor —
   both activate automatically once credentials are supplied and degrade cleanly, never
   fabricating imagery, when they aren't.

See [Architecture](architecture.md) for the full system design, [API Reference](api.md)
for endpoint details, and [Deployment](deployment.md) to run it yourself.
