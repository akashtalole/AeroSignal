import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { aqiColor } from "../utils/aqi.js";

// Plain Leaflet (not react-leaflet) wrapped by hand with a ref + useEffect,
// per the project's design brief. Markers are color-coded by the best AQI
// reading known for each corridor (live, once analyzed; baseline
// otherwise), and clicking one selects that corridor.
//
// This is the always-available, no-API-key default map (OpenStreetMap
// tiles, no Google Maps Platform key needed). `MapView.jsx` picks this
// component unless VITE_GOOGLE_MAPS_API_KEY is set at build time, in which
// case it renders `GoogleMap.jsx` instead — see MapView.jsx.
export function LeafletMap({ corridors, aqiById, selectedId, onSelect, satelliteTileUrl }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const satelliteLayerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { zoomControl: true, worldCopyJump: true }).setView([18, 60], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = {};
      satelliteLayerRef.current = null;
    };
  }, []);

  // Optional Earth Engine tile overlay (Sentinel-2 true-color or NDVI) on
  // top of the OSM base tiles, added/removed as the selected corridor or
  // layer choice changes. `satelliteTileUrl` is null when no corridor is
  // selected, Earth Engine isn't available for this deployment, or the
  // user has toggled the overlay off — in every one of those cases this
  // just removes any existing overlay and leaves the base map untouched.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (satelliteLayerRef.current) {
      map.removeLayer(satelliteLayerRef.current);
      satelliteLayerRef.current = null;
    }
    if (satelliteTileUrl) {
      satelliteLayerRef.current = L.tileLayer(satelliteTileUrl, { opacity: 0.85, maxZoom: 18 }).addTo(map);
    }
  }, [satelliteTileUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const seenIds = new Set(corridors.map((c) => c.id));
    for (const [id, marker] of Object.entries(markersRef.current)) {
      if (!seenIds.has(id)) {
        map.removeLayer(marker);
        delete markersRef.current[id];
      }
    }

    corridors.forEach((c) => {
      const aqi = aqiById[c.id] ?? c.baseline_aqi;
      const color = aqiColor(aqi);
      const isSelected = c.id === selectedId;
      const size = isSelected ? 22 : 15;
      const icon = L.divIcon({
        className: "",
        html: `<div class="corridor-dot${isSelected ? " selected" : ""}" style="width:${size}px;height:${size}px;background:${color}"></div>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
      });

      let marker = markersRef.current[c.id];
      const tooltipText = `${c.corridor} (${c.country}) — AQI ${Math.round(aqi)}`;
      if (!marker) {
        marker = L.marker([c.lat, c.lng], { icon }).addTo(map);
        marker.on("click", () => onSelect(c.id));
        marker.bindTooltip(tooltipText, { direction: "top", offset: [0, -size / 2] });
        markersRef.current[c.id] = marker;
      } else {
        marker.setIcon(icon);
        marker.setTooltipContent(tooltipText);
      }
    });
  }, [corridors, aqiById, selectedId, onSelect]);

  return <div className="map-view" ref={containerRef} role="img" aria-label="Map of BRICS corridors color-coded by air quality" />;
}
