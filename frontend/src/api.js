const BASE = "/api";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getCorridors: () => request("/corridors"),
  analyze: (corridor_id, scenario) =>
    request("/analyze", {
      method: "POST",
      body: JSON.stringify({ corridor_id, scenario: scenario || null }),
    }),
  translate: (text, target_lang) =>
    request("/translate", { method: "POST", body: JSON.stringify({ text, target_lang }) }),
  getSatellite: (corridor_id) => request(`/corridors/${encodeURIComponent(corridor_id)}/satellite`),
  streamUrl: (corridor_id, scenario) => {
    const params = new URLSearchParams({ corridor_id });
    if (scenario) params.set("scenario", JSON.stringify(scenario));
    return `${BASE}/analyze/stream?${params.toString()}`;
  },
};
