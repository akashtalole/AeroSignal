# Hackathon Submission

**Event:** Code for Communities — Second Edition (hack2skill, BRICS Agentic Platform)
**Track:** Track 2 — Clean Air & Climate Resilience (BRICS theme: Sustainability)

## Brief description

**AeroSignal** is a multi-agent AI system (Google ADK + Gemini, via Vertex AI or AI
Studio) that turns live air-quality and satellite data into decisions — not another
dashboard. It monitors 9 Indian states in real time, simulates traffic interventions
before they're tried, and proactively drafts health advisories the moment air quality
turns hazardous, with voice and multilingual support built in.

## Links

- **Live demo:** https://track2-clean-air-climate-719250423519.us-central1.run.app/
- **Source code:** https://github.com/akashtalole/aerosignal
- **Demo video script & pitch deck:** see [`submission/`](https://github.com/akashtalole/aerosignal/tree/main/submission)
  in the repository — includes the full scene-by-scene SSML demo-video script and the
  pitch deck source.

## Judging rubric alignment

| Criterion | Weight | How AeroSignal addresses it |
|---|---|---|
| Problem-Solution Fit | 20% | Targets a documented, large-scale public-health problem (1.67M deaths/yr in India from air pollution) with a tool that acts, not just monitors. |
| AI/Technical Execution | 25% | Real multi-agent Google ADK pipeline (`ParallelAgent`, `LoopAgent`, self-critique loop) with live, streamed agent traces — not a single LLM call. |
| Depth & Reach Across India | 20% | 9 Indian states live today (Delhi, Maharashtra, Karnataka, West Bengal, Tamil Nadu, Gujarat, Telangana, Uttar Pradesh, Bihar); adding a new corridor is one data row. |
| Impact Potential | 15% | Proactive advisory drafting + what-if intervention simulator turn monitoring into actionable policy planning for city officials. |
| Deployability & Scalability | 20% | One-command Cloud Run deployment (`deploy.sh`), zero-API-key Vertex AI/ADC mode for API-key-restricted orgs, graceful degradation at every external dependency. |

## Mandatory requirements

- ✅ **Functioning end-to-end flow** — live, deployed on Cloud Run.
- ✅ **Mandatory Google AI integration** — Gemini via Google ADK (Vertex AI/ADC or
  AI Studio key).
- ✅ **Real/realistic data** — live Open-Meteo air-quality and weather data; real
  Google Earth Engine Sentinel-2 satellite imagery when configured.
- ✅ **Built for India** — 9-state coverage, India-first UI, scales by adding one
  corridor record.
- ✅ **Multilingual/voice support** — English/Hindi/Tamil toggle, native
  `SpeechSynthesis` read-aloud.
