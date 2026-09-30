# Deployment

## Local development

Requires Python 3.11+ and Node.js 18+.

```bash
# Terminal 1 - backend (port 8788)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8788
# optional: export GEMINI_API_KEY=... to enable the real ADK multi-agent pipeline
# (or, with no API keys allowed, see "Vertex AI" below for the ADC path)

# Terminal 2 - frontend (port 5174, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5174`.

## Google Cloud Run

```bash
./deploy.sh PROJECT_ID
```

`deploy.sh` builds the Docker image, enables required APIs (including
`aiplatform.googleapis.com`), deploys to Cloud Run, and — when no `GEMINI_API_KEY` is
provided — automatically configures **Vertex AI + Application Default Credentials**
(`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`) plus
the IAM grants the service's own Cloud Run service account needs
(`roles/aiplatform.user`, `roles/serviceusage.serviceUsageConsumer`). No key of any kind
is required for Gemini to work in this mode.

## Optional: Google Maps Platform & Earth Engine

Both upgrades are **off by default** — the app is fully functional without either — and
turn on automatically once a deploying user supplies the right credentials. Neither is
ever faked: without real tiles/imagery you get the existing Leaflet map or an honest
"not available" note.

### Google Maps Platform (real map tiles + markers)

1. Get a Maps JavaScript API key (Google Cloud Console → APIs & Services →
   Credentials), restricted by **HTTP referrer** to your deployed domain.
2. Build the frontend with it baked in:
   - Local dev: `cd frontend && VITE_GOOGLE_MAPS_API_KEY=your-key npm run build` (or
     `frontend/.env.local`).
   - Docker: `docker build --build-arg GOOGLE_MAPS_API_KEY=your-key -t aerosignal .`
3. `gcloud run deploy --source` does not reliably pass Docker `--build-arg` values
   through to a Dockerfile's `ARG`, so for Cloud Run, build and push the image yourself
   first:

```bash
docker build --build-arg GOOGLE_MAPS_API_KEY=your-key \
  -t REGION-docker.pkg.dev/PROJECT_ID/REPO/aerosignal .
docker push REGION-docker.pkg.dev/PROJECT_ID/REPO/aerosignal

DEPLOY_IMAGE=REGION-docker.pkg.dev/PROJECT_ID/REPO/aerosignal ./deploy.sh PROJECT_ID
```

(Requires an Artifact Registry Docker repo:
`gcloud artifacts repositories create REPO --repository-format=docker --location=REGION`.)

### Google Earth Engine (real Sentinel-2 / NDVI imagery)

1. **Register your GCP project for Earth Engine** at
   https://code.earthengine.google.com — a manual, one-time step.
2. **Grant Earth Engine access** to the Cloud Run service's default service account.
   `deploy.sh` does this automatically (`roles/serviceusage.serviceUsageConsumer`), or
   grant it by hand:

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"
```

3. Set `GOOGLE_CLOUD_PROJECT` to your registered project id (`deploy.sh` does this
   automatically).
4. `GET /api/corridors/{id}/satellite` starts returning real Sentinel-2 imagery, and the
   map's Satellite control shows working "True color" / "NDVI" toggles.

If Earth Engine isn't registered or the IAM grant is missing, `backend/earth_engine.py`
catches that at startup and the satellite endpoint always returns
`{"available": false, "reason": "..."}` — the rest of the app is unaffected.
