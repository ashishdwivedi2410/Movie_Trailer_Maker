/* =========================================================
   validate.js — Client-side validation before submit.
   Checks required fields and basic file-type extensions.
   Backend should still re-validate everything server-side.
   ========================================================= */

const SUBTITLE_EXTENSIONS = [".srt", ".vtt"];
const DOC_EXTENSIONS = [".json", ".pdf"];

function hasExtension(filename, extensions) {
  const lower = filename.toLowerCase();
  return extensions.some((ext) => lower.endsWith(ext));
}

/**
 * @param {object} state - output of collectFormState() plus category/dialect
 * @returns {Array<{field: string, message: string}>}
 */
export function validateTrailerForm(state) {
  const errors = [];

  if (!state.episodeFiles || state.episodeFiles.length === 0) {
    errors.push({
      field: "input-episode-files",
      message: "Upload at least one episode video or clip."
    });
  }

  if (!state.sceneDescriptions?.trim() && !state.sceneDescriptionsFile) {
    errors.push({
      field: "scene-descriptions",
      message: "Add scene descriptions as text, or upload a file."
    });
  }

  if (!state.dialogueText?.trim()) {
    errors.push({
      field: "dialogue-text",
      message: "Enter the source dialogue."
    });
  }

  if (!state.subtitleDialect1) {
    errors.push({
      field: "subtitle-dialect-1",
      message: "Upload the first dialect subtitle track (.srt/.vtt)."
    });
  } else if (!hasExtension(state.subtitleDialect1.name, SUBTITLE_EXTENSIONS)) {
    errors.push({
      field: "subtitle-dialect-1",
      message: "Subtitle file must be .srt or .vtt."
    });
  }

  if (!state.subtitleDialect2) {
    errors.push({
      field: "subtitle-dialect-2",
      message: "Upload the second dialect subtitle track (.srt/.vtt)."
    });
  } else if (!hasExtension(state.subtitleDialect2.name, SUBTITLE_EXTENSIONS)) {
    errors.push({
      field: "subtitle-dialect-2",
      message: "Subtitle file must be .srt or .vtt."
    });
  }

  if (!state.ratingPoliciesFile) {
    errors.push({
      field: "rating-policies-file",
      message: "Upload a rating policies file (.json or .pdf)."
    });
  } else if (!hasExtension(state.ratingPoliciesFile.name, DOC_EXTENSIONS)) {
    errors.push({
      field: "rating-policies-file",
      message: "Rating policies file must be .json or .pdf."
    });
  }

  if (!state.contractsFile) {
    errors.push({
      field: "contracts-file",
      message: "Upload a contracts file (.json or .pdf)."
    });
  } else if (!hasExtension(state.contractsFile.name, DOC_EXTENSIONS)) {
    errors.push({
      field: "contracts-file",
      message: "Contracts file must be .json or .pdf."
    });
  }

  if (!state.category) {
    errors.push({
      field: "category-group",
      message: "Select a trailer category."
    });
  }

  if (state.category === "dialect_region" && !state.dialect) {
    errors.push({
      field: "dialect-input",
      message: "Enter the dialect for the regional campaign."
    });
  }

  return errors;
}

/** Renders inline error messages next to each invalid field. */
export function showFieldErrors(errors) {
  document.querySelectorAll(".field-error").forEach((el) => el.remove());
  document.querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));

  errors.forEach(({ field, message }) => {
    const input = document.getElementById(field);
    if (!input) return;

    input.classList.add("is-invalid");

    const msg = document.createElement("p");
    msg.className = "field-error";
    msg.dataset.for = field;
    msg.textContent = message;
    input.insertAdjacentElement("afterend", msg);
  });
}

/** Removes the error (and red outline) from one field. Safe to call on any element. */
export function clearFieldError(el) {
  if (!el || !el.id) return;
  el.classList.remove("is-invalid");
  document.querySelectorAll(".field-error").forEach((msg) => {
    if (msg.dataset.for === el.id) msg.remove();
  });
}

/** Clears a field's error as soon as the user edits or fixes it, instead of waiting for the next submit. */
export function initLiveErrorClearing(form) {
  const handler = (event) => {
    const target = event.target;
    clearFieldError(target.closest(".is-invalid") || target);
    // Changing the category also invalidates any stale dialect error.
    if (target.name === "category") clearFieldError(document.getElementById("dialect-input"));
  };
  form.addEventListener("input", handler);
  form.addEventListener("change", handler);
}