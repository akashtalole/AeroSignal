import { SpeakableText } from "./SpeakableText.jsx";

// The proactive-escalation feature: an advisory drafted automatically
// whenever AQI crosses the hazard threshold, without anyone asking for it.
export function AlertsPanel({ alert }) {
  if (!alert) {
    return (
      <div className="panel alerts-panel calm">
        <h2>Alerts</h2>
        <p className="muted">No active alert — AQI is within the hazard threshold for this corridor.</p>
      </div>
    );
  }

  return (
    <div className={`panel alerts-panel level-${alert.level}`}>
      <div className="panel-header">
        <h2>Proactive Advisory</h2>
        <span className={`alert-level-badge level-${alert.level}`}>{alert.level.toUpperCase()}</span>
      </div>
      <dl className="alert-meta">
        <dt>Authority</dt>
        <dd>{alert.authority}</dd>
        <dt>Current / 48h max AQI</dt>
        <dd>
          {alert.aqi_now} / {alert.aqi_48h_max} (threshold {alert.threshold})
        </dd>
        {alert.affected_neighbors.length > 0 && (
          <>
            <dt>Cross-border / neighboring corridors</dt>
            <dd>{alert.affected_neighbors.join(", ")}</dd>
          </>
        )}
      </dl>
      <SpeakableText text={alert.message} />
    </div>
  );
}
