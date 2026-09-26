/* =========================================================
   api.js — All backend communication lives here.
   Swap API_BASE for the real backend URL when available.
   Every other module only talks to the backend through
   the functions exported from this file.
   ========================================================= */

export const API_BASE = "/api"; // TODO: replace with real backend base URL

async function postFormData(url, formData) {
  const res = await fetch(url, {
    method: "POST",
    body: formData
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${text || res.statusText}`);
  }
  return res.json();
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status}): ${res.statusText}`);
  }
  return res.json();
}

/** Submit all collected inputs + category/dialect as multipart form data. */
export async function submitTrailerRequest(formData) {
  return postFormData(`${API_BASE}/generate-trailer`, formData);
}

/** Poll for status if the backend supports async/long-running jobs. */
export async function fetchTrailerStatus(trailerId) {
  return getJSON(`${API_BASE}/trailer-status/${encodeURIComponent(trailerId)}`);
}

/** Dialect list for the "Dialect-region viewers" dropdown. */
export async function fetchDialects() {
  try {
    return await getJSON(`${API_BASE}/dialects`);
  } catch (err) {
    // Placeholder fallback until the backend/dialect list is wired up
    return ["Dialect A", "Dialect B", "Dialect C"];
  }
}

/** Read-only reference data — fetched instead of uploaded, when available. */
export async function fetchAudienceProfiles() {
  return getJSON(`${API_BASE}/audience-profiles`);
}

export async function fetchHistoricPerformance() {
  return getJSON(`${API_BASE}/historic-performance`);
}

export async function fetchCostSheet() {
  return getJSON(`${API_BASE}/cost-sheet`);
}