// Shared US-AQI helpers: color bands (green/yellow/orange/red/maroon) used
// consistently by the map markers, dashboard badge, and simulation bars.

export function aqiColor(aqi) {
  if (aqi == null) return "#9ca3af";
  if (aqi <= 50) return "#22c55e"; // Good
  if (aqi <= 100) return "#eab308"; // Moderate
  if (aqi <= 150) return "#f97316"; // Unhealthy for Sensitive Groups
  if (aqi <= 200) return "#ef4444"; // Unhealthy
  return "#7f1d1d"; // Very Unhealthy / Hazardous
}

export function aqiTextColor(aqi) {
  if (aqi == null) return "#111827";
  return aqi <= 100 ? "#111827" : "#f9fafb";
}

const AGENT_LABELS = {
  air_quality_monitor: "Air Quality Monitor",
  weather_context: "Weather Context",
  health_impact_analyst: "Health Impact Analyst",
  intervention_simulator: "Intervention Simulator",
  synthesis_agent: "Synthesis Agent",
  critic_agent: "Critic Agent",
  escalation: "Escalation",
  synthesis_review_loop: "Synthesis Review Loop",
  clean_air_data_collection: "Data Collection",
  clean_air_climate_pipeline: "Pipeline",
};

export function agentLabel(agent) {
  return AGENT_LABELS[agent] || agent;
}
