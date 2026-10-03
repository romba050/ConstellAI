const API_BASE =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
  "http://127.0.0.1:8787";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "content-type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const detail =
      typeof body === "string"
        ? body
        : body?.detail || body?.message || JSON.stringify(body);
    throw new Error(detail || `request failed: ${res.status}`);
  }

  return body;
}

export async function getHistoricalReplayBank() {
  return request("/api/rare/history/bank", { method: "GET" });
}

export async function seedHistoricalReplayBank() {
  return request("/api/rare/history/seed", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function replayHistoricalCase(payload) {
  return request("/api/rare/history/replay", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function storeHistoricalHit(payload) {
  return request("/api/rare/history/store-hit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function trainHistoricalReplay(payload) {
  return request("/api/rare/history/train", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
