#!/usr/bin/env bash
# Deploys Track 2 (Clean Air & Climate Resilience) to Cloud Run as a
# single service — one command, no other setup needed beyond a GCP project
# with billing enabled.
#
# Usage (from Cloud Shell, after cloning this repo):
#   cd track-2-clean-air-climate
#   ./deploy.sh <PROJECT_ID> [REGION] [SERVICE_NAME]
#
# Or export GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION first and just run
# ./deploy.sh with no arguments.
#
# Live Gemini reasoning (the ADK multi-agent pipeline, not just the offline
# fallback) needs ONE of two things — this script sets both up so it works
# either way, no action needed unless your org disallows API keys (see below):
#
#   - GEMINI_API_KEY (Google AI Studio) — set it before running this script
#     to use it, OR
#   - Vertex AI + Application Default Credentials — the default whenever no
#     GEMINI_API_KEY is set. This script always enables the Vertex AI API and
#     passes GOOGLE_GENAI_USE_VERTEXAI=TRUE + GOOGLE_CLOUD_PROJECT +
#     GOOGLE_CLOUD_LOCATION to the service, and best-effort grants the
#     project's default Cloud Run service account the "Vertex AI User" role
#     (roles/aiplatform.user) so it can call Gemini using its OWN identity —
#     no key of any kind, which is exactly what's required when an org
#     policy has "API Keys are Disallowed" (Google Cloud Console → APIs &
#     Services → Credentials will say this explicitly if that's your case).
#     If the IAM grant below fails (e.g. you don't have
#     resourcemanager.projects.setIamPolicy on this project), ask a project
#     owner to run the one `gcloud projects add-iam-policy-binding` command
#     this script prints, then just re-run this script — everything else
#     about the deploy is unaffected either way, and the app runs correctly
#     on its offline fallback in the meantime.
#
# Two further OPTIONAL upgrades, both off by default (the app is fully
# functional without either — see README.md):
#
#   - Earth Engine satellite/NDVI imagery: this script always passes
#     GOOGLE_CLOUD_PROJECT to the service, which is all real Earth Engine
#     access needs (it uses the attached service account's Application
#     Default Credentials) — PROVIDED you have separately (a) registered
#     this GCP project for Earth Engine at https://code.earthengine.google.com
#     and (b) granted the Cloud Run service's default service account an
#     Earth Engine role (e.g. "Earth Engine Resource Viewer") in IAM. Both
#     are manual, one-time steps this script cannot do for you. Without
#     them, the satellite endpoint just returns an honest "not available"
#     response — nothing breaks.
#
#   - Google Maps Platform: set GOOGLE_MAPS_API_KEY before running this
#     script to build the frontend with a real Google Maps map. IMPORTANT:
#     `gcloud run deploy --source` builds via Cloud Build's source-deploy
#     path, which does NOT reliably support passing a Docker `--build-arg`
#     into a Dockerfile-based build (its `--set-build-env-vars` family of
#     flags is for buildpacks' build environment, not Dockerfile ARGs, and
#     is not confirmed to reach `ARG GOOGLE_MAPS_API_KEY` in this
#     Dockerfile). Rather than silently ship something unverified, this
#     script does NOT attempt to pass the key through `--source` deploys.
#     If you want the Google Maps upgrade, build and push the image
#     yourself first — see "Enabling the Google Maps Platform upgrade" in
#     README.md for the exact commands — then re-run this script with
#     DEPLOY_IMAGE set to that image, which this script will deploy with
#     `gcloud run deploy --image` instead of `--source` (skipping the
#     build step here entirely).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${2:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
SERVICE_NAME="${3:-track2-clean-air-climate}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: no project id. Usage: ./deploy.sh <PROJECT_ID> [REGION] [SERVICE_NAME]" >&2
  echo "  or: export GOOGLE_CLOUD_PROJECT=your-project-id" >&2
  exit 1
fi

echo "==> Project:  ${PROJECT_ID}"
echo "==> Region:   ${REGION}"
echo "==> Service:  ${SERVICE_NAME}"

gcloud config set project "${PROJECT_ID}" >/dev/null

echo "==> Enabling required APIs (safe to re-run)"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com \
  --project "${PROJECT_ID}"

ENV_VARS="NODE_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE"
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  ENV_VARS="${ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY}"
  echo "==> GEMINI_API_KEY provided — live Gemini reasoning will use it directly."
else
  echo "==> No GEMINI_API_KEY set — live Gemini reasoning will use Vertex AI + this"
  echo "    service's own Application Default Credentials instead (see below)."

  # Best-effort: grant the default Cloud Run/Compute service account Vertex AI
  # access so ADC actually works without any key. Never fails the deploy —
  # if this doesn't have permission, the app still runs fine on its offline
  # fallback until a project owner runs the printed command by hand.
  PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null || true)"
  if [[ -n "${PROJECT_NUMBER}" ]]; then
    DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    GRANT_CMD="gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:${DEFAULT_SA} --role=roles/aiplatform.user"
    echo "==> Granting Vertex AI User to ${DEFAULT_SA} (safe to re-run)"
    if ${GRANT_CMD} >/dev/null 2>&1; then
      echo "==> Granted. This service account can now call Gemini via Vertex AI with no key."
    else
      echo "==> WARNING: could not grant the role automatically (likely a permissions issue" >&2
      echo "    on your account, not a problem with the app). Ask a project owner to run:" >&2
      echo "      ${GRANT_CMD}" >&2
      echo "    then re-run this script — everything else about the deploy is unaffected." >&2
    fi
  fi
fi

# Earth Engine's own IAM prerequisite — separate from (and needed regardless
# of) the Vertex AI grant above: confirmed via a real deploy that Earth
# Engine's own EEException names this exact role when it's missing
# ("Grant the caller the roles/serviceusage.serviceUsageConsumer role").
# Best-effort, never fails the deploy — the satellite endpoint degrades to
# an honest "not available" response either way (see earth_engine.py).
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null || true)"
if [[ -n "${PROJECT_NUMBER}" ]]; then
  DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  EE_GRANT_CMD="gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:${DEFAULT_SA} --role=roles/serviceusage.serviceUsageConsumer"
  echo "==> Granting Service Usage Consumer to ${DEFAULT_SA} for Earth Engine (safe to re-run)"
  if ${EE_GRANT_CMD} >/dev/null 2>&1; then
    echo "==> Granted. Combined with a project registered for Earth Engine, the satellite"
    echo "    layer should work (allow a few minutes for the grant to propagate)."
  else
    echo "==> WARNING: could not grant the role automatically (likely a permissions issue" >&2
    echo "    on your account, not a problem with the app). Ask a project owner to run:" >&2
    echo "      ${EE_GRANT_CMD}" >&2
    echo "    The satellite endpoint reports an honest 'not available' note until then." >&2
  fi
fi

# GOOGLE_CLOUD_PROJECT (above) is what backend/earth_engine.py needs to
# attempt ee.Initialize() — it will only actually succeed if this project
# has been registered for Earth Engine and this service's service account
# has Earth Engine access (see the header comment above). If either isn't
# true, the app degrades cleanly: the satellite endpoint just reports
# unavailable, nothing else is affected.

if [[ -n "${GOOGLE_MAPS_API_KEY:-}" && -z "${DEPLOY_IMAGE:-}" ]]; then
  echo "==> WARNING: GOOGLE_MAPS_API_KEY is set, but 'gcloud run deploy --source' cannot" >&2
  echo "    reliably pass it into the Dockerfile as a build-arg (see this script's header" >&2
  echo "    comment and README.md). It will be IGNORED for this deploy — the app will" >&2
  echo "    build and run fine, just without the Google Maps upgrade. Build your own" >&2
  echo "    image with --build-arg and set DEPLOY_IMAGE to use it instead." >&2
fi

if [[ -n "${DEPLOY_IMAGE:-}" ]]; then
  echo "==> Deploying pre-built image ${DEPLOY_IMAGE} to ${SERVICE_NAME} (no build step)"
  gcloud run deploy "${SERVICE_NAME}" \
    --image "${DEPLOY_IMAGE}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars="${ENV_VARS}"
else
  echo "==> Building and deploying ${SERVICE_NAME} (this builds the Docker image via Cloud Build)"
  gcloud run deploy "${SERVICE_NAME}" \
    --source "${SCRIPT_DIR}" \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars="${ENV_VARS}"
fi

echo ""
echo "==> Deployed. The service URL is printed above — open it in a browser."
