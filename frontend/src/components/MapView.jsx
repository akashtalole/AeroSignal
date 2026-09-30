import { useCallback, useState } from "react";
import { LeafletMap } from "./LeafletMap.jsx";
import { GoogleMap } from "./GoogleMap.jsx";

// Vite bakes VITE_* env vars into the client bundle at `npm run build` time.
// When unset (the default, and always true for anyone who hasn't supplied
// their own Google Maps Platform key), this is undefined and the app is
// byte-for-byte the same Leaflet/OSM experience it has always been — the
// GoogleMap code path is never imported into a running branch, let alone
// given a key.
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

// Picks between the always-available Leaflet/OSM map and the optional
// Google Maps upgrade. If the Google Maps script fails to load for any
// reason (bad key, HTTP-referrer restriction misconfigured, network
// blocked), this falls back to LeafletMap rather than showing a broken map.
export function MapView(props) {
  const [googleMapsFailed, setGoogleMapsFailed] = useState(false);

  const handleGoogleMapsLoadError = useCallback((err) => {
    // eslint-disable-next-line no-console
    console.warn("Google Maps failed to load — falling back to OpenStreetMap:", err?.message || err);
    setGoogleMapsFailed(true);
  }, []);

  if (GOOGLE_MAPS_API_KEY && !googleMapsFailed) {
    return <GoogleMap apiKey={GOOGLE_MAPS_API_KEY} onLoadError={handleGoogleMapsLoadError} {...props} />;
  }
  return <LeafletMap {...props} />;
}
