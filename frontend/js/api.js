/* =========================================================
   api.js — All backend communication lives here.
   Every other module only talks to the backend through
   the functions exported from this file.

   Backend routes (backend/src/api.py):
     POST /api/generate-trailer  -> one trailer object
   ========================================================= */

// Same-origin by default (nginx proxies /api to the backend). To point the
// page at another origin, set window.TRAILER_API_BASE before loading main.js,
// e.g. "http://localhost:8000/api" (the backend then needs CORS_ORIGINS set).
export const API_BASE = window.TRAILER_API_BASE || "/api";

// Backend form-field names -> DOM ids, so server-side validation errors can
// be shown next to the right input.
const FIELD_IDS = {
  episode_files: "input-episode-files",
  scene_descriptions: "scene-descriptions",
  scene_descriptions_file: "scene-descriptions-file",
  dialogue_text: "dialogue-text",
  subtitle_dialect_1: "subtitle-dialect-1",
  subtitle_dialect_2: "subtitle-dialect-2",
  rating_policies_file: "rating-policies-file",
  contracts_file: "contracts-file",
  audience_profiles_file: "audience-profiles-file",
  historic_performance_file: "historic-performance-file",
  cost_sheet_file: "cost-sheet-file",
  category: "category-group",
  dialect: "dialect-input"
};

/** Error thrown for any failed backend call. `fieldErrors` is [{field: <DOM id>, message}]. */
export class ApiError extends Error {
  constructor(message, { status = 0, fieldErrors = [] } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function errorFromResponse(res) {
  let detail = null;
  try {
    detail = (await res.json()).detail;
  } catch (err) {
    // body was not JSON; fall through to the status text
  }

  if (Array.isArray(detail)) {
    // Our own validation errors: [{field, message}]. FastAPI's built-in ones
    // look like [{loc, msg}] and have no `field`.
    const fieldErrors = detail
      .filter((d) => d && d.field)
      .map((d) => ({ field: FIELD_IDS[d.field] || d.field, message: d.message }));
    const messages = detail.map((d) => d.message || d.msg).filter(Boolean);
    return new ApiError(messages.join(" ") || res.statusText, { status: res.status, fieldErrors });
  }
  if (typeof detail === "string" && detail) {
    return new ApiError(detail, { status: res.status });
  }
  return new ApiError(`Request failed (${res.status}): ${res.statusText}`, { status: res.status });
}

async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new ApiError("Could not reach the server. Check that the backend is running.");
  }
  if (!res.ok) throw await errorFromResponse(res);
  return res.json();
}

/** Submit all collected inputs + category/dialect as multipart form data. Resolves to ONE trailer object. */
export async function submitTrailerRequest(formData) {
  return request(`${API_BASE}/generate-trailer`, { method: "POST", body: formData });
}