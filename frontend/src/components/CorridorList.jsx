import { useMemo, useState } from "react";
import { aqiColor } from "../utils/aqi.js";

// Built for India, scaling across states: India's corridors are sorted
// first and the filter defaults to showing all of them, with a one-line
// stat making the India-scale coverage visible immediately.
export function CorridorList({ corridors, aqiById, selectedId, onSelect }) {
  const [filter, setFilter] = useState("all");

  const indiaStates = useMemo(
    () => new Set(corridors.filter((c) => c.country === "India").map((c) => c.state)).size,
    [corridors],
  );
  const otherCorridors = corridors.length - corridors.filter((c) => c.country === "India").length;

  const sorted = useMemo(() => {
    const list = filter === "india" ? corridors.filter((c) => c.country === "India") : corridors;
    return [...list].sort((a, b) => {
      if (a.country === "India" && b.country !== "India") return -1;
      if (a.country !== "India" && b.country === "India") return 1;
      return a.corridor.localeCompare(b.corridor);
    });
  }, [corridors, filter]);

  return (
    <div className="corridor-list-panel">
      <div className="india-stat">
        🇮🇳 Live across <strong>{indiaStates} Indian states</strong>
        <span className="muted"> · +{otherCorridors} other BRICS corridors</span>
      </div>
      <div className="corridor-filter" role="group" aria-label="Filter corridors">
        <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>
          All corridors
        </button>
        <button className={filter === "india" ? "active" : ""} onClick={() => setFilter("india")}>
          India only
        </button>
      </div>
      <ul className="corridor-list">
        {sorted.map((c) => {
          const aqi = aqiById[c.id] ?? c.baseline_aqi;
          return (
            <li key={c.id}>
              <button
                className={c.id === selectedId ? "corridor-chip active" : "corridor-chip"}
                onClick={() => onSelect(c.id)}
              >
                <span className="chip-dot" style={{ background: aqiColor(aqi) }} />
                <span className="chip-name">
                  {c.corridor}
                  <span className="muted small">
                    {" "}
                    — {c.state ? `${c.state}, ` : ""}
                    {c.country}
                  </span>
                </span>
                <span className="chip-aqi">{Math.round(aqi)}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
