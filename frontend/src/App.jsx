import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { MapView } from "./components/MapView.jsx";
import { SatelliteLayer } from "./components/SatelliteLayer.jsx";
import { CorridorList } from "./components/CorridorList.jsx";
import { AgentTrace } from "./components/AgentTrace.jsx";
import { AqiDashboard } from "./components/AqiDashboard.jsx";
import { SimulationPanel } from "./components/SimulationPanel.jsx";
import { AlertsPanel } from "./components/AlertsPanel.jsx";
import { NarrativePanel } from "./components/NarrativePanel.jsx";

const DEFAULT_SCENARIO = { heavy_vehicle_reduction_pct: 0, restricted_hours: 0, green_corridor_km: 0 };
const SCENARIO_DEBOUNCE_MS = 450;

export default function App() {
  const [corridors, setCorridors] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [result, setResult] = useState(null);
  const [trace, setTrace] = useState([]);
  const [activeAgent, setActiveAgent] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [aqiById, setAqiById] = useState({});
  const [loadError, setLoadError] = useState(null);
  const [mode, setMode] = useState("offline");
  const [satellite, setSatellite] = useState(null);
  const [satelliteLayer, setSatelliteLayer] = useState(null); // null | "rgb" | "ndvi"

  const esRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    api
      .getCorridors()
      .then(setCorridors)
      .catch((e) => setLoadError(e.message));
    return () => {
      if (esRef.current) esRef.current.close();
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Optional Earth Engine satellite layer: fetched per-corridor, resets
  // whenever the selection changes. A false/failed result is stored as-is
  // (SatelliteLayer renders its honest "not available" note) — never
  // treated as an error state for the rest of the app.
  useEffect(() => {
    setSatelliteLayer(null);
    if (!selectedId) {
      setSatellite(null);
      return;
    }
    setSatellite(null);
    let cancelled = false;
    api
      .getSatellite(selectedId)
      .then((data) => {
        if (!cancelled) setSatellite(data);
      })
      .catch((e) => {
        if (!cancelled) setSatellite({ available: false, reason: e.message });
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const applyResult = useCallback((res) => {
    setResult(res);
    setMode(res.mode);
    setAqiById((prev) => ({
      ...prev,
      [res.corridor.id]: res.air_quality.current.us_aqi ?? res.air_quality.aqi_48h_max,
    }));
  }, []);

  const runStream = useCallback(
    (corridorId) => {
      if (esRef.current) esRef.current.close();
      setTrace([]);
      setActiveAgent(null);
      setStreaming(true);
      setResult(null);

      const es = new EventSource(api.streamUrl(corridorId, null));
      esRef.current = es;
      es.onmessage = (evt) => {
        const data = JSON.parse(evt.data);
        if (data.type === "final") {
          applyResult(data);
          setActiveAgent(null);
          setStreaming(false);
          es.close();
        } else {
          setActiveAgent(data.agent);
          setTrace((prev) => [...prev, data]);
        }
      };
      es.onerror = () => {
        setStreaming(false);
        es.close();
      };
    },
    [applyResult],
  );

  function selectCorridor(id) {
    setSelectedId(id);
    setScenario(DEFAULT_SCENARIO);
    runStream(id);
  }

  function updateScenario(next) {
    setScenario(next);
    if (!selectedId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.analyze(selectedId, next);
        applyResult(res);
      } catch (e) {
        setLoadError(e.message);
      }
    }, SCENARIO_DEBOUNCE_MS);
  }

  const selectedCorridor = corridors.find((c) => c.id === selectedId) || null;
  const satelliteTileUrl =
    satelliteLayer && satellite?.available ? satellite[satelliteLayer === "rgb" ? "tile_url_rgb" : "tile_url_ndvi"] : null;

  if (loadError) {
    return (
      <div className="app-error">
        <h1>AeroSignal</h1>
        <p>Could not reach the API: {loadError}</p>
        <p className="muted">Make sure the backend is running.</p>
      </div>
    );
  }

  if (corridors.length === 0) {
    return <div className="app-loading">Loading AeroSignal...</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>AeroSignal</h1>
          <p className="muted">
            A multi-agent AI platform for clean air &amp; climate resilience — built for India, scaling across
            states, and framed for BRICS-wide cross-border coordination.
          </p>
        </div>
      </header>

      <main className="layout">
        <section className="left-col">
          <MapView
            corridors={corridors}
            aqiById={aqiById}
            selectedId={selectedId}
            onSelect={selectCorridor}
            satelliteTileUrl={satelliteTileUrl}
          />
          <SatelliteLayer
            corridorId={selectedId}
            satellite={satellite}
            activeLayer={satelliteLayer}
            onChangeLayer={setSatelliteLayer}
          />
          <CorridorList corridors={corridors} aqiById={aqiById} selectedId={selectedId} onSelect={selectCorridor} />
        </section>

        <section className="right-col">
          <AlertsPanel alert={result?.alert} />
          <AqiDashboard result={result} corridor={selectedCorridor} />
          <NarrativePanel narrative={result?.narrative} />
          <AgentTrace trace={trace} activeAgent={activeAgent} streaming={streaming} mode={mode} />
          <SimulationPanel scenario={scenario} onChange={updateScenario} result={result} disabled={!selectedId} />
        </section>
      </main>
    </div>
  );
}
