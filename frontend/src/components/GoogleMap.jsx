import { useEffect, useRef, useState } from "react";
import { aqiColor } from "../utils/aqi.js";
import { loadGoogleMapsScript } from "../utils/loadGoogleMaps.js";

// Optional upgrade over LeafletMap, used only when a build-time
// VITE_GOOGLE_MAPS_API_KEY was supplied (see MapView.jsx). Reproduces the
// same corridor markers/AQI-color-coding as LeafletMap, on the real Google
// Maps JavaScript API. Uses the classic `google.maps.Marker` rather than
// `AdvancedMarkerElement` — more reliable without a registered Map ID, and
// this app doesn't need Advanced Markers' extra features.
//
// If the script fails to load (bad/missing key, network error, referrer
// restriction misconfigured), `onLoadError` is called and MapView.jsx falls
// back to LeafletMap — this component never renders a broken/blank map.

function svgDotIcon(color, size) {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">` +
    `<circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 1.5}" fill="${color}" ` +
    `stroke="white" stroke-width="2"/></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function GoogleMap({ apiKey, corridors, aqiById, selectedId, onSelect, onLoadError, satelliteTileUrl }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const infoWindowRef = useRef(null);
  const overlayRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGoogleMapsScript(apiKey)
      .then(() => {
        if (cancelled || !containerRef.current) return;
        const google = window.google;
        mapRef.current = new google.maps.Map(containerRef.current, {
          center: { lat: 18, lng: 60 },
          zoom: 2,
        });
        infoWindowRef.current = new google.maps.InfoWindow();
        setReady(true);
      })
      .catch((err) => {
        if (!cancelled) onLoadError?.(err);
      });
    return () => {
      cancelled = true;
      // The Maps JS API has no map-teardown call; drop refs so a future
      // remount builds a fresh map instance rather than reusing a stale one.
      mapRef.current = null;
      markersRef.current = {};
      overlayRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    const google = window.google;
    const map = mapRef.current;

    const seenIds = new Set(corridors.map((c) => c.id));
    for (const [id, marker] of Object.entries(markersRef.current)) {
      if (!seenIds.has(id)) {
        marker.setMap(null);
        delete markersRef.current[id];
      }
    }

    corridors.forEach((c) => {
      const aqi = aqiById[c.id] ?? c.baseline_aqi;
      const color = aqiColor(aqi);
      const isSelected = c.id === selectedId;
      const size = isSelected ? 22 : 15;
      const tooltipText = `${c.corridor} (${c.country}) — AQI ${Math.round(aqi)}`;
      const icon = {
        url: svgDotIcon(color, size),
        scaledSize: new google.maps.Size(size, size),
        anchor: new google.maps.Point(size / 2, size / 2),
      };

      let marker = markersRef.current[c.id];
      if (!marker) {
        marker = new google.maps.Marker({
          position: { lat: c.lat, lng: c.lng },
          map,
          icon,
          title: tooltipText,
        });
        marker.addListener("click", () => onSelect(c.id));
        marker.addListener("mouseover", () => {
          infoWindowRef.current.setContent(tooltipText);
          infoWindowRef.current.open({ anchor: marker, map });
        });
        marker.addListener("mouseout", () => infoWindowRef.current.close());
        markersRef.current[c.id] = marker;
      } else {
        marker.setIcon(icon);
        marker.setTitle(tooltipText);
      }
    });
  }, [ready, corridors, aqiById, selectedId, onSelect]);

  // Optional Earth Engine tile overlay, mirrored from LeafletMap's
  // equivalent effect — see its comment for what satelliteTileUrl means.
  // google.maps.ImageMapType wants a getTileUrl(coord, zoom) function
  // rather than a {z}/{x}/{y} template string, and expects non-negative,
  // wrapped tile X coordinates at the antimeridian.
  useEffect(() => {
    if (!ready || !mapRef.current) return;
    const google = window.google;
    const map = mapRef.current;

    if (overlayRef.current) {
      const idx = map.overlayMapTypes.getArray().indexOf(overlayRef.current);
      if (idx >= 0) map.overlayMapTypes.removeAt(idx);
      overlayRef.current = null;
    }

    if (satelliteTileUrl) {
      const imageMapType = new google.maps.ImageMapType({
        getTileUrl: (coord, zoom) => {
          const tileCount = Math.pow(2, zoom);
          if (coord.y < 0 || coord.y >= tileCount) return null;
          let x = coord.x % tileCount;
          if (x < 0) x += tileCount;
          return satelliteTileUrl.replace("{z}", zoom).replace("{x}", x).replace("{y}", coord.y);
        },
        tileSize: new google.maps.Size(256, 256),
        opacity: 0.85,
        name: "Earth Engine",
      });
      map.overlayMapTypes.insertAt(0, imageMapType);
      overlayRef.current = imageMapType;
    }
  }, [ready, satelliteTileUrl]);

  return (
    <div
      className="map-view"
      ref={containerRef}
      role="img"
      aria-label="Map of BRICS corridors color-coded by air quality (Google Maps)"
    />
  );
}
