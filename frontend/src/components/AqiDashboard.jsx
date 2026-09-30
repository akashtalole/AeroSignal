import { aqiColor, aqiTextColor } from "../utils/aqi.js";

const POLLUTANTS = [
  { key: "pm2_5", label: "PM2.5", unit: "µg/m³", ceiling: 250 },
  { key: "pm10", label: "PM10", unit: "µg/m³", ceiling: 430 },
  { key: "nitrogen_dioxide", label: "NO2", unit: "µg/m³", ceiling: 400 },
  { key: "ozone", label: "O3", unit: "µg/m³", ceiling: 400 },
  { key: "carbon_monoxide", label: "CO", unit: "µg/m³", ceiling: 30000 },
];

function Sparkline({ points }) {
  if (!points || points.length < 2) {
    return <p className="muted small">No 48h forecast available (cached baseline mode).</p>;
  }
  const width = 320;
  const height = 64;
  const values = points.map((p) => p.us_aqi);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const coords = points.map((p, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = height - ((p.us_aqi - min) / span) * (height - 8) - 4;
    return [x, y];
  });
  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lastX, lastY] = coords[coords.length - 1];

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2" />
      <circle cx={lastX} cy={lastY} r="3.5" fill={aqiColor(values[values.length - 1])} />
    </svg>
  );
}

export function AqiDashboard({ result, corridor }) {
  if (!corridor) {
    return (
      <div className="panel aqi-dashboard">
        <h2>Air Quality Dashboard</h2>
        <p className="muted">Select a corridor on the map to see its live air quality.</p>
      </div>
    );
  }

  const aq = result?.air_quality;
  const current = aq?.current;
  const aqi = current?.us_aqi ?? corridor.baseline_aqi;
  const band = aq?.aqi_band ?? "—";
  const color = aqiColor(aqi);

  return (
    <div className="panel aqi-dashboard">
      <div className="panel-header">
        <h2>{corridor.corridor}</h2>
        <span className="muted small">
          {corridor.state ? `${corridor.state}, ` : ""}
          {corridor.country}
        </span>
      </div>

      <div className="aqi-hero">
        <div className="aqi-number" style={{ background: color, color: aqiTextColor(aqi) }}>
          {Math.round(aqi)}
        </div>
        <div>
          <div className="aqi-band-badge" style={{ borderColor: color, color }}>
            {band}
          </div>
          {result && (
            <p className="muted small">
              data source: {result.data_source === "live" ? "live Open-Meteo feed" : "cached corridor baseline"}
            </p>
          )}
        </div>
      </div>

      {current && (
        <div className="pollutant-bars">
          {POLLUTANTS.map(({ key, label, unit, ceiling }) => {
            const value = current[key];
            const pct = value == null ? 0 : Math.min(100, (value / ceiling) * 100);
            return (
              <div className="pollutant-row" key={key}>
                <span className="pollutant-label">{label}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
                <span className="pollutant-value">{value != null ? `${value} ${unit}` : "—"}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="sparkline-wrap">
        <span className="muted small">48h AQI forecast</span>
        <Sparkline points={aq?.forecast_48h} />
      </div>
    </div>
  );
}
