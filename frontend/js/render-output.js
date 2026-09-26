/* =========================================================
   render-output.js — Takes the trailer JSON returned by the
   backend (matching the agreed schema) and renders:
   - the playable video
   - the validation/status banner
   - the creative brief
   - the segment-by-segment EDL table
   ========================================================= */

function formatStatusClass(status) {
  if (!status) return "";
  const normalized = status.toLowerCase();
  if (normalized.includes("pass") && normalized.includes("warning")) return "pass-with-warnings";
  if (normalized.includes("fail")) return "fail";
  if (normalized.includes("pass")) return "pass";
  return "";
}

function escapeHTML(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderVideo(videoUrl) {
  const video = document.getElementById("trailer-video");
  if (!video) return;

  if (videoUrl) {
    video.src = videoUrl;
    video.hidden = false;
  } else {
    video.hidden = true;
  }
}

function renderStatusBanner(status) {
  const el = document.getElementById("status-banner");
  if (!el) return;
  el.textContent = status || "UNKNOWN";
  el.className = `status-banner ${formatStatusClass(status)}`;
}

function renderBrief(trailer) {
  const brief = document.getElementById("creative-brief");
  if (!brief) return;

  brief.innerHTML = `
    <dl class="brief-grid">
      <dt>Trailer ID</dt><dd>${escapeHTML(trailer.trailer_id) || "—"}</dd>
      <dt>Audience</dt><dd>${escapeHTML(trailer.audience) || "—"}</dd>
      <dt>Duration</dt><dd>${trailer.duration_seconds ?? "—"}s</dd>
      <dt>Central promise</dt><dd>${escapeHTML(trailer.audience_promise) || "—"}</dd>
    </dl>
  `;
}

function renderEDLTable(segments) {
  const body = document.getElementById("edl-table-body");
  if (!body) return;
  body.innerHTML = "";

  (segments || []).forEach((seg) => {
    const tr = document.createElement("tr");

    const riskFlags = (seg.risk_flags || [])
      .map((flag) => `<span class="risk-flag">${escapeHTML(flag)}</span>`)
      .join("");

    tr.innerHTML = `
      <td class="timecodes">${escapeHTML(seg.source_in)} – ${escapeHTML(seg.source_out)}</td>
      <td>${escapeHTML(seg.video)}</td>
      <td>${escapeHTML(seg.audio)}</td>
      <td>${escapeHTML(seg.subtitle)}</td>
      <td>${escapeHTML(seg.reason)}</td>
      <td>${(seg.evidence || []).map(escapeHTML).join(", ")}</td>
      <td>${riskFlags}</td>
    `;
    body.appendChild(tr);
  });
}

function renderNotes(trailer) {
  const notes = document.getElementById("notes-block");
  if (!notes) return;

  const warnings = trailer.warnings || [];
  const approvals = trailer.required_approvals || [];
  const cost = trailer.estimated_cost;
  const fallback = trailer.cost_fallback_plan;

  const warningsHTML = warnings.length
    ? `<h3>Warnings & assumptions</h3><ul>${warnings.map((w) => `<li>${escapeHTML(w)}</li>`).join("")}</ul>`
    : "";

  const approvalsHTML = approvals.length
    ? `<h3>Approvals still required</h3><ul>${approvals.map((a) => `<li>${escapeHTML(a)}</li>`).join("")}</ul>`
    : "";

  const costHTML = cost !== undefined
    ? `<h3>Cost</h3>
       <div class="cost-line"><span>Estimated processing cost</span><span>${escapeHTML(String(cost))}</span></div>
       ${fallback ? `<p class="meta">Fallback: ${escapeHTML(fallback)}</p>` : ""}`
    : "";

  notes.innerHTML = warningsHTML + approvalsHTML + costHTML;
}

/** Main entry point: pass in the trailer object returned by the backend. */
export function renderTrailerOutput(trailer) {
  renderVideo(trailer.video_url);
  renderStatusBanner(trailer.validation?.status);
  renderBrief(trailer);
  renderEDLTable(trailer.segments);
  renderNotes(trailer);

  const outputSection = document.getElementById("output-section");
  if (outputSection) outputSection.hidden = false;
}