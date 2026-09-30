# AeroSignal — Demo Video Script (Track 2: Clean Air & Climate Resilience)

This is the exact script used for the delivered demo video (`AeroSignal_demo.mp4`,
~2:59), recorded as a real screen capture against the live deployed app
(https://track2-clean-air-climate-719250423519.us-central1.run.app/) with narration
synthesized per scene and muxed onto the real recording — not a mockup. 9 scenes, each
below with its actual SSML block (compatible with Amazon Polly or any SSML-capable
TTS — `espeak-ng -m` was used for this recording, in a neutral en-US voice).

At the time of recording, this deployment had no `GEMINI_API_KEY`/Vertex AI configured,
so it was running the real offline fallback pipeline — real Open-Meteo data throughout,
deterministic (non-LLM) narration. The script says so explicitly in scene 4 rather than
overclaiming live LLM reasoning that wasn't actually happening on screen. If you
re-record after enabling Vertex AI/`GEMINI_API_KEY` (see `../README.md`), scene 4 can be
tightened to describe the live critic/revision loop directly.

Google Earth Engine access was granted between the first and second recording — scene 3
below reflects the second, final recording, which shows the real "True color" satellite
toggle actually being switched on (with its real computed date range visible on screen).

---

## Scene 1 — Cold open (0:00–0:17)

**Screen:** App homepage — map, corridor list, "Live across 9 Indian states" banner.

```xml
<speak><p>Every day, hundreds of millions of people in Indian cities breathe air
that would trigger a health emergency almost anywhere else.<break time="500ms"/></p>
<p>This is AeroSignal <break time="150ms"/> a multi agent A I platform for clean air
and climate resilience, built for India and scaled across states.</p></speak>
```

## Scene 2 — The problem (0:17–0:33)

**Screen:** Hold on the homepage/map.

```xml
<speak><p>The Lancet's India State Level Disease Burden study attributes one point
six seven million deaths a year in India to air pollution.<break time="300ms"/></p>
<p>Most tools stop at a dashboard, a number with no way to act on it.<break time="300ms"/></p>
<p>We built something that acts.</p></speak>
```

## Scene 3 — Real, live data + live satellite imagery (0:33–0:58)

**Screen:** Click the "Delhi-NCR Corridor" chip. Dashboard populates with live AQI,
pollutant bars, and the 48h forecast sparkline. Then click the "True color" button on
the Sentinel-2 satellite toggle above the corridor list.

```xml
<speak><p>Let's select a live corridor. <break time="400ms"/> Delhi N C R.<break time="600ms"/></p>
<p>This A Q I of one hundred fifty six, and every pollutant reading below it, is
fetched live from Open Meteo the moment the corridor is selected. <break time="300ms"/>
Not seeded, not mocked, live.<break time="300ms"/></p>
<p>And now, real Google Earth Engine satellite imagery too <break time="200ms"/> a live
Sentinel-2 composite for this exact date window, toggled on right here.</p></speak>
```

## Scene 4 — The multi-agent pipeline (0:58–1:31)

**Screen:** Scroll to the Assessment + Agent Trace panels, showing all 6 pipeline steps.

```xml
<speak><p>Scroll down, and you can see exactly what happened behind that number.
<break time="400ms"/></p>
<p>This is a real multi agent pipeline built on Google's Agent Development Kit.
<break time="300ms"/>
An Air Quality Monitor and a Weather Context agent ran, fetching live data.
<break time="200ms"/>
A Health Impact Analyst scored the exposure risk. <break time="200ms"/>
And a Synthesis agent assembled the final assessment.<break time="300ms"/></p>
<p>This deployment is running its offline safe pipeline right now, with no Gemini
key configured <break time="200ms"/> and the architecture, and every real data
point, is exactly the same either way.</p></speak>
```

## Scene 5 — Proactive advisory (1:31–1:49)

**Screen:** Proactive Advisory panel (already populated — MODERATE, auto-drafted).

```xml
<speak><p>And notice this. <break time="400ms"/> Nobody asked for an alert.<break time="300ms"/></p>
<p>The moment A Q I crossed the hazard threshold of one fifty, the system
automatically drafted this proactive advisory <break time="200ms"/>
naming the responsible authority, and flagging neighboring corridors for
coordinated response.</p></speak>
```

## Scene 6 — What-if simulation (1:49–2:07)

**Screen:** What-If Intervention Simulator. Move the sliders (heavy-vehicle reduction
30%, restricted hours 6h, green corridor 2km) — projected AQI recomputes live (155 → 127.7 in the recorded run).

```xml
<speak><p>Now watch this. <break time="400ms"/></p>
<p>A city official can simulate an intervention before trying it in the real world.
<break time="300ms"/>
Heavy vehicle traffic reduction. <break time="200ms"/> Restricted hours.
<break time="200ms"/> A new green corridor.<break time="400ms"/></p>
<p>And the projected air quality impact recomputes instantly <break time="200ms"/>
turning a monitoring app into a planning tool.</p></speak>
```

## Scene 7 — Voice + language (2:07–2:20)

**Screen:** Click the हिंदी language toggle, then the 🔊 Read aloud button.

```xml
<speak><p>Every assessment can be read aloud right in the browser, no extra
service, no extra cost.<break time="250ms"/></p>
<p>The language toggle is ready for Hindi and Tamil the moment a Gemini key is
added <break time="150ms"/> honest either way.</p></speak>
```

## Scene 8 — India-scale (2:20–2:39)

**Screen:** Click "India only" filter, scroll the corridor list, click back to
"All corridors."

```xml
<speak><p>This isn't a one city demo. <break time="400ms"/></p>
<p>Nine Indian states are live today, from Gujarat to Bihar, <break time="200ms"/>
alongside eight corridors across Brazil, Russia, China, South Africa and Egypt
<break time="200ms"/> for cross border B R I C S coordination.<break time="300ms"/></p>
<p>Every new city is one row of data away.</p></speak>
```

## Scene 9 — Close (2:39–2:47)

**Screen:** Scroll back to the top/homepage.

```xml
<speak><p>AeroSignal.<break time="300ms"/></p>
<p>Real data. Real multi agent A I. A decision, not just a dashboard.<break time="400ms"/></p>
<p>Thank you.</p></speak>
```

---

## How this was produced (for anyone re-recording after enabling live Gemini)

1. A headless Chromium (Playwright) session drove the actual deployed URL, performing
   the click/scroll/slider actions described per scene, holding each screen state for
   as long as that scene's narration takes.
2. Each scene's SSML above was synthesized to audio (`espeak-ng -m -f scene.ssml -w
   scene.wav -v en-us -s 160..168`), concatenated with short silence gaps between
   scenes.
3. The screen recording (webm) and the concatenated narration (wav → aac) were muxed
   together with `ffmpeg` into the final mp4.
4. Any TTS engine that accepts SSML (Amazon Polly included) can synthesize the same
   blocks above directly — nothing here is espeak-ng-specific except the exact voice
   name used for the reference recording.
