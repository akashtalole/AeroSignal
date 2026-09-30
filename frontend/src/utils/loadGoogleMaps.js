// Loads the Google Maps JavaScript API dynamically, on demand — never a
// static <script> tag in index.html, so it is only ever fetched (and the
// key only ever leaves the browser) when a deployer has actually set
// VITE_GOOGLE_MAPS_API_KEY. Maps JavaScript API keys are designed to be
// client-visible: they're restricted by HTTP referrer in the Google Cloud
// Console, not treated as a secret.
//
// A singleton in-flight promise means multiple GoogleMap mounts (or a
// remount in dev-mode StrictMode) share one script load instead of
// injecting the tag twice.

let loadPromise = null;

export function loadGoogleMapsScript(apiKey) {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Maps can only load in a browser"));
  }
  if (window.google?.maps?.Map) {
    return Promise.resolve(window.google);
  }
  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-google-maps-loader]");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.google));
      existing.addEventListener("error", () =>
        reject(new Error("Google Maps script failed to load (network error or invalid key)")),
      );
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=marker&v=weekly`;
    script.async = true;
    script.defer = true;
    script.dataset.googleMapsLoader = "true";
    script.onload = () => {
      if (window.google?.maps?.Map) {
        resolve(window.google);
      } else {
        reject(new Error("Google Maps script loaded but google.maps is unavailable (invalid key?)"));
      }
    };
    script.onerror = () => reject(new Error("Google Maps script failed to load (network error or invalid key)"));
    document.head.appendChild(script);
  }).catch((err) => {
    // Allow a future retry (e.g. after the key is fixed and the page
    // reloads) instead of caching a permanent failure.
    loadPromise = null;
    throw err;
  });

  return loadPromise;
}
