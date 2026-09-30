import { agentLabel } from "../utils/aqi.js";

// Makes the multi-agent orchestration genuinely visible: each step arrives
// live over the /api/analyze/stream SSE connection and is appended here as
// it happens, with a pulsing dot on whichever agent is currently active.
export function AgentTrace({ trace, activeAgent, streaming, mode }) {
  return (
    <div className="panel agent-trace">
      <div className="panel-header">
        <h2>Agent Trace</h2>
        <span className={`mode-badge mode-${mode}`}>{mode === "gemini" ? "Live ADK pipeline" : "Offline pipeline"}</span>
      </div>
      {trace.length === 0 && !streaming && (
        <p className="muted">Select a corridor on the map to run the multi-agent pipeline.</p>
      )}
      <ul className="trace-list">
        {trace.map((step, i) => {
          const isActive = streaming && step.agent === activeAgent && i === trace.length - 1;
          return (
            <li key={i} className={isActive ? "active" : ""}>
              <span className={`trace-dot${isActive ? " pulsing" : ""}`} />
              <div>
                <strong>{agentLabel(step.agent)}</strong>
                <p>{step.summary}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
