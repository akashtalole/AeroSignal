# Submission materials — Track 2: Clean Air & Climate Resilience

This folder holds the non-code deliverables for the hack2skill submission package,
alongside the actual application code in `../backend/` and `../frontend/`.

## Files here

- **`brief-description.md`** — the 2-3 line solution summary for the submission form.
- **`demo-video-script.md`** — the full demo video script: 8 scenes, screen-recording
  directions, and an Amazon Polly SSML block per scene. The recorded video itself
  (`AeroSignal_demo.mp4`, ~2:54, real narration muxed over a real screen capture of the
  deployed app) was delivered separately in chat — upload it to YouTube/Drive and link
  it in the submission form per hack2skill's "Demo video" requirement; it isn't
  committed here since binary video files don't belong in a source repo.
- **`pitch-deck/`** — the pitch deck's **source** (`deck.json` + one HTML file per
  slide, 12 slides total: problem, solution, architecture, AI execution, real data,
  what-if simulation, proactive alerts, India/Maharashtra scale, deployability,
  impact, close). This is what actually defines the deck's content.

## Getting an actual .pptx / .pdf file to upload

The deck lives as an interactive Claude Artifact, not a binary file — that's what
the `pitch-deck/` source above renders into. To get a `.pptx` or `.pdf` for the
hack2skill upload:

1. Open the deck: **https://claude.ai/artifact/RoczMCqcFvzAPtPscC4Rmg**
2. Use **Share → Export** and pick PowerPoint or PDF.

That link is currently **private** (visible only to the account that created it) —
if you want to share the link itself rather than an exported file, open it and use
the page's own **Share** menu to change that; sharing settings can only be changed
from the page itself, not by Claude.

## Brief description

See `brief-description.md` — same text as below, kept in sync:

> **AeroSignal** is a multi-agent AI system (Google ADK + Gemini, Vertex AI or AI
> Studio) that turns live air-quality and satellite data into decisions — not
> another dashboard. It monitors 9 Indian states in real time, simulates traffic
> interventions before they're tried, and proactively drafts health advisories the
> moment air quality turns hazardous, with voice and multilingual support built in.
