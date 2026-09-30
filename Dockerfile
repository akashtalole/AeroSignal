# Multi-stage build: compile the React frontend, then serve it as static
# files from the same FastAPI backend that serves /api — one container,
# one Cloud Run service, no CORS to configure.

FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Optional Google Maps Platform upgrade: if GOOGLE_MAPS_API_KEY is passed as
# a build arg, Vite bakes it into the built bundle so the frontend loads the
# real Google Maps JS API instead of Leaflet/OSM. Left empty (the default),
# the build is byte-for-byte the same as before — see README.md.
ARG GOOGLE_MAPS_API_KEY=""
ENV VITE_GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist ./public

ENV PORT=8080
EXPOSE 8080
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
