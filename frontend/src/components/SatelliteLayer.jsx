// Small control panel for the optional Google Earth Engine imagery layer.
// Purely a display/toggle component — App.jsx owns the fetch (via
// api.getSatellite) and hands down the result, so MapView and this panel
// stay in sync off one source of truth.
//
// Never shows a fabricated image or an alarming error: when Earth Engine
// isn't configured for this deployment (the sandbox/default case, and any
// deployment without a registered GCP project), it shows one honest,
// calm sentence and the toggle buttons simply don't render.
export function SatelliteLayer({ corridorId, satellite, activeLayer, onChangeLayer }) {
  if (!corridorId) return null;

  if (!satellite) {
    return <div className="satellite-layer muted">Checking Earth Engine satellite imagery…</div>;
  }

  if (!satellite.available) {
    return (
      <div className="satellite-layer satellite-layer--unavailable">
        <span className="muted">
          Satellite imagery not available — {satellite.reason || "Earth Engine is not configured for this deployment."}
        </span>
      </div>
    );
  }

  return (
    <div className="satellite-layer">
      <span className="satellite-layer__label">Sentinel-2 satellite ({satellite.date_range}):</span>
      <div className="satellite-layer__buttons" role="group" aria-label="Satellite imagery layer">
        <button type="button" className={activeLayer === null ? "active" : ""} onClick={() => onChangeLayer(null)}>
          Off
        </button>
        <button type="button" className={activeLayer === "rgb" ? "active" : ""} onClick={() => onChangeLayer("rgb")}>
          True color
        </button>
        <button
          type="button"
          className={activeLayer === "ndvi" ? "active" : ""}
          onClick={() => onChangeLayer("ndvi")}
        >
          NDVI
        </button>
      </div>
    </div>
  );
}
