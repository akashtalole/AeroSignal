# AeroSignal

**Multi-agent AI for Clean Air & Climate Resilience — built for India, framed for BRICS**

[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://akashtalole.github.io/aerosignal/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

> Submitted to **Code for Communities — Second Edition** (hack2skill, BRICS Agentic
> Platform) — Track 2: Clean Air & Climate Resilience.
>
> Live demo: https://track2-clean-air-climate-719250423519.us-central1.run.app/
> Full docs: https://akashtalole.github.io/aerosignal/

AeroSignal is a multi-agent AI platform for clean air and climate resilience, built for
India — scaling across 9 Indian states — and framed as a BRICS-wide system for
cross-border coordination. A Python [Google ADK](https://github.com/google/adk-python)
agent pipeline fetches real, live air-quality and weather data, scores public-health
risk, lets an authority simulate a traffic/emissions intervention before committing to
it, and proactively drafts a public-health advisory the moment air quality crosses a
hazard threshold — without anyone having to ask for one.

## The problem

Major BRICS cities monitor macro-level air quality but consistently miss hyper-local and
cross-border pollution events — industrial emissions, large-scale agricultural burning,
trans-boundary smog. The absence of real-time, granular data and of tools to evaluate an
intervention *before* deploying it prevents coordinated, evidence-based climate action.
The Lancet's India State-Level Disease Burden study attributes **1.67 million deaths a
year in India** to air pollution.

## What it does

1. **A genuine multi-agent ADK pipeline**, not a single classifier call —
   `air_quality_monitor` and `weather_context` fan out as a `ParallelAgent`,
   `health_impact_analyst` scores risk, `intervention_simulator` projects what-if
   scenarios, and `synthesis_agent` + `critic_agent` run in a `LoopAgent` so the final
   assessment self-reviews for internal consistency before it ships.
2. **Real external data, with honest fallback.** Every analysis calls Open-Meteo's free
   Air Quality + Weather APIs live; if a call fails, the response falls back to a
   corridor's static baseline and is clearly marked `data_source: "cached_baseline"`
   instead of `"live"` — never a hard failure.
3. **Live, visible agent orchestration.** `GET /api/analyze/stream` streams the
   pipeline's real ADK `Event` objects over Server-Sent Events; the frontend's Agent
   Trace panel renders each step as it happens.
4. **What-if intervention simulation** — heavy-vehicle traffic reduction, restricted
   hours, new green-corridor km — recomputes projected AQI instantly, turning a
   monitoring app into a planning tool.
5. **Proactive escalation.** The moment AQI crosses the hazard threshold (150), the
   system automatically drafts a public-health advisory naming the responsible authority
   and flagging neighboring corridors — nobody has to ask for it.
6. **Built for India, scaling across states.** 9 of 17 tracked corridors are Indian
   (Delhi, Maharashtra, Karnataka, West Bengal, Tamil Nadu, Gujarat, Telangana, Uttar
   Pradesh, Bihar), alongside 8 other BRICS corridors for cross-border framing.
7. **Multilingual & voice support.** Assessments read aloud via the browser's native
   `SpeechSynthesis` API (no key needed); toggle between English, Hindi, and Tamil.
8. **Optional Google Geo upgrades** — real Google Maps tiles and real Google Earth
   Engine Sentinel-2/NDVI satellite imagery, both off by default and degrading cleanly
   (never faked) when credentials aren't supplied.

See the [full documentation](https://akashtalole.github.io/aerosignal/) for
architecture, API reference, deployment, and the Google AI/Vertex integration details.

## Quick start

Requires Python 3.11+ and Node.js 18+.

```bash
# Terminal 1 - backend (port 8788)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8788
# optional: export GEMINI_API_KEY=... to enable the real ADK multi-agent pipeline

# Terminal 2 - frontend (port 5174, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5174`. See [docs/deployment.md](docs/deployment.md) for
Google Cloud Run deployment via `deploy.sh`, including Vertex AI/ADC (no API key) mode
and the optional Google Maps / Earth Engine setup.

## Google AI integration

Runs Gemini through Google's **Agent Development Kit (ADK)** — `LlmAgent`,
`ParallelAgent`, `LoopAgent` — either via `GEMINI_API_KEY` (Google AI Studio) or, for
orgs that disallow API keys, **Vertex AI + Application Default Credentials** with zero
keys at all. If a live Gemini call ever fails, every endpoint falls back to the same
real-data offline path rather than erroring, honestly reporting `"mode": "offline"`.

## Tech stack

- **Backend**: Python, FastAPI, `google-adk`, Open-Meteo APIs, optional Google Earth
  Engine
- **Frontend**: React, Vite, Leaflet (optional Google Maps), native `SpeechSynthesis`
- **Deploy**: Docker, Google Cloud Run (`deploy.sh`)
- **Docs**: MkDocs Material, GitHub Pages

## Repository layout

```
backend/      FastAPI + ADK multi-agent pipeline
frontend/     React + Vite SPA
docs/         MkDocs documentation source
submission/   Hackathon submission materials (pitch deck, demo script, brief description)
Dockerfile    Production container build
deploy.sh     Google Cloud Run deployment script
mkdocs.yml    Docs site config (deployed to GitHub Pages)
```

## License

[MIT](./LICENSE)
