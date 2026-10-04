/* =========================================================
   main.js — App entry point. Wires together inputs,
   validation, the category selector, the API call, the
   processing state, and output rendering.
   ========================================================= */

import { submitTrailerRequest, ApiError } from "./api.js";
import { initCategorySelector, getSelectedCategory, getSelectedDialect } from "./category.js";
import { collectFormState, buildFormData, initFileListDisplays } from "./inputs.js";
import { validateTrailerForm, showFieldErrors } from "./validate.js";
import { renderTrailerOutput } from "./render-output.js";

// Placeholder stage labels shown while waiting on the backend.
// Replace with real progress updates once the backend reports stage-by-stage status.
const STAGES = [
  "Uploading files",
  "Validating inputs",
  "Generating trailer segments",
  "Running rights, policy & bias checks",
  "Building creative brief & EDL",
  "Finalizing output"
];

function showProcessing() {
  const section = document.getElementById("processing-section");
  const list = document.getElementById("stage-list");
  const output = document.getElementById("output-section");
  const errorState = document.getElementById("error-state");

  if (output) output.hidden = true;
  if (errorState) errorState.hidden = true;
  if (!section || !list) return;

  list.innerHTML = "";
  STAGES.forEach((stage, i) => {
    const li = document.createElement("li");
    li.textContent = stage;
    li.className = i === 0 ? "active" : "";
    list.appendChild(li);
  });
  section.hidden = false;
}

function advanceStage(index) {
  const list = document.getElementById("stage-list");
  if (!list) return;
  Array.from(list.children).forEach((li, i) => {
    li.className = i < index ? "done" : i === index ? "active" : "";
  });
}

function hideProcessing() {
  const section = document.getElementById("processing-section");
  if (section) section.hidden = true;
}

function showError(message) {
  const errorState = document.getElementById("error-state");
  const errorMessage = document.getElementById("error-message");
  hideProcessing();
  if (errorMessage) errorMessage.textContent = message;
  if (errorState) errorState.hidden = false;
}

function setSubmitting(isSubmitting) {
  const btn = document.getElementById("submit-btn");
  if (!btn) return;
  btn.disabled = isSubmitting;
  btn.textContent = isSubmitting ? "Processing…" : "Generate Trailer";
}

async function handleSubmit(event) {
  event.preventDefault();

  const state = collectFormState();
  const category = getSelectedCategory();
  const dialect = getSelectedDialect();

  const errors = validateTrailerForm({ ...state, category, dialect });
  showFieldErrors(errors);
  if (errors.length > 0) {
    document.getElementById(errors[0].field)?.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const formData = buildFormData(state, category, dialect);

  setSubmitting(true);
  showProcessing();

  // Simulated stage progression — swap for real progress polling once the
  // backend reports stage-by-stage status (it currently answers in one request).
  let stageIndex = 1;
  const stageTimer = setInterval(() => {
    if (stageIndex < STAGES.length) {
      advanceStage(stageIndex);
      stageIndex++;
    }
  }, 1200);

  try {
    const trailer = await submitTrailerRequest(formData);
    clearInterval(stageTimer);
    advanceStage(STAGES.length);
    hideProcessing();
    renderTrailerOutput(trailer);
  } catch (err) {
    clearInterval(stageTimer);
    if (err instanceof ApiError && err.fieldErrors.length > 0) {
      // Server-side validation caught something the browser checks did not.
      showFieldErrors(err.fieldErrors);
      document.getElementById(err.fieldErrors[0].field)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    showError(err.message || "Something went wrong while generating the trailer.");
  } finally {
    setSubmitting(false);
  }
}

function initRetry() {
  const retryBtn = document.getElementById("retry-btn");
  if (!retryBtn) return;
  retryBtn.addEventListener("click", () => {
    document.getElementById("error-state").hidden = true;
  });
}

function init() {
  const form = document.getElementById("trailer-form");
  if (form) form.addEventListener("submit", handleSubmit);
  initFileListDisplays();
  initCategorySelector();
  initRetry();
}

document.addEventListener("DOMContentLoaded", init);