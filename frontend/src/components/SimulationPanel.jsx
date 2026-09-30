import { aqiColor } from "../utils/aqi.js";

const MAX_AQI_SCALE = 250; // bar-chart scale ceiling shared by baseline/projected bars

export function SimulationPanel({ scenario, onChange, result, disabled }) {
  const sim = result?.simulation;

  function set(field, value) {
    onChange({ ...scenario, [field]: value });
  }

  return (
    <div className="panel simulation-panel">
      <h2>What-If Intervention Simulator</h2>
      <p className="muted small">
        Move the sliders to project the AQI impact of a traffic/emissions intervention against this corridor's
        current baseline.
      </p>

      <div className="slider-row">
        <label htmlFor="hv-reduction">
          Heavy-vehicle traffic reduction <strong>{scenario.heavy_vehicle_reduction_pct}%</strong>
        </label>
        <input
          id="hv-reduction"
          type="range"
          min="0"
          max="100"
          step="5"
          value={scenario.heavy_vehicle_reduction_pct}
          disabled={disabled}
          onChange={(e) => set("heavy_vehicle_reduction_pct", Number(e.target.value))}
        />
      </div>

      <div className="slider-row">
        <label htmlFor="restricted-hours">
          Traffic-restricted hours/day <strong>{scenario.restricted_hours}h</strong>
        </label>
        <input
          id="restricted-hours"
          type="range"
          min="0"
          max="24"
          step="1"
          value={scenario.restricted_hours}
          disabled={disabled}
          onChange={(e) => set("restricted_hours", Number(e.target.value))}
        />
      </div>

      <div className="slider-row">
        <label htmlFor="green-corridor">
          New green corridor <strong>{scenario.green_corridor_km}km</strong>
        </label>
        <input
          id="green-corridor"
          type="range"
          min="0"
          max="10"
          step="0.5"
          value={scenario.green_corridor_km}
          disabled={disabled}
          onChange={(e) => set("green_corridor_km", Number(e.target.value))}
        />
      </div>

      {sim ? (
        <div className="sim-compare">
          <div className="sim-bar-row">
            <span className="sim-bar-label">Baseline</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(100, (sim.baseline_aqi / MAX_AQI_SCALE) * 100)}%`, background: aqiColor(sim.baseline_aqi) }}
              />
            </div>
            <strong>{sim.baseline_aqi}</strong>
          </div>
          <div className="sim-bar-row">
            <span className="sim-bar-label">Projected</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(100, (sim.projected_aqi / MAX_AQI_SCALE) * 100)}%`, background: aqiColor(sim.projected_aqi) }}
              />
            </div>
            <strong>{sim.projected_aqi}</strong>
          </div>
          <p className={`sim-delta ${sim.delta_aqi <= 0 ? "improve" : "worsen"}`}>
            {sim.delta_aqi <= 0 ? "▼" : "▲"} {Math.abs(sim.delta_aqi)} AQI ({sim.percent_change}%) — now{" "}
            {sim.projected_aqi_band}
          </p>
          <p className="muted small">{sim.note}</p>
        </div>
      ) : (
        <p className="muted">{disabled ? "Select a corridor first." : "Move a slider to see the projected impact."}</p>
      )}
    </div>
  );
}
