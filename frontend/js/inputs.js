/* =========================================================
   inputs.js — Reads the 8 input sections from the DOM,
   builds the FormData payload sent to the backend, and
   handles the small "selected files" list under each
   file upload.
   ========================================================= */

/** Reads every input field's current value/files into a plain state object. */
export function collectFormState() {
  const get = (id) => document.getElementById(id);

  const episodeInput = get("input-episode-files");
  const sceneTextarea = get("scene-descriptions");
  const sceneFile = get("scene-descriptions-file");
  const dialogueTextarea = get("dialogue-text");
  const subtitle1 = get("subtitle-dialect-1");
  const subtitle2 = get("subtitle-dialect-2");
  const ratingFile = get("rating-policies-file");
  const contractsFile = get("contracts-file");
  const audienceFile = get("audience-profiles-file");
  const historicFile = get("historic-performance-file");
  const costFile = get("cost-sheet-file");

  return {
    episodeFiles: episodeInput?.files.length ? Array.from(episodeInput.files) : [],
    sceneDescriptions: sceneTextarea ? sceneTextarea.value : "",
    sceneDescriptionsFile: sceneFile?.files[0] || null,
    dialogueText: dialogueTextarea ? dialogueTextarea.value : "",
    subtitleDialect1: subtitle1?.files[0] || null,
    subtitleDialect2: subtitle2?.files[0] || null,
    ratingPoliciesFile: ratingFile?.files[0] || null,
    contractsFile: contractsFile?.files[0] || null,
    audienceProfilesFile: audienceFile?.files[0] || null,
    historicPerformanceFile: historicFile?.files[0] || null,
    costSheetFile: costFile?.files[0] || null
  };
}

/** Turns the collected state + category/dialect into a multipart FormData payload. */
export function buildFormData(state, category, dialect) {
  const fd = new FormData();

  state.episodeFiles.forEach((file, i) => fd.append(`episode_files[${i}]`, file));
  fd.append("scene_descriptions", state.sceneDescriptions);
  if (state.sceneDescriptionsFile) fd.append("scene_descriptions_file", state.sceneDescriptionsFile);
  fd.append("dialogue_text", state.dialogueText);
  if (state.subtitleDialect1) fd.append("subtitle_dialect_1", state.subtitleDialect1);
  if (state.subtitleDialect2) fd.append("subtitle_dialect_2", state.subtitleDialect2);
  if (state.ratingPoliciesFile) fd.append("rating_policies_file", state.ratingPoliciesFile);
  if (state.contractsFile) fd.append("contracts_file", state.contractsFile);
  if (state.audienceProfilesFile) fd.append("audience_profiles_file", state.audienceProfilesFile);
  if (state.historicPerformanceFile) fd.append("historic_performance_file", state.historicPerformanceFile);
  if (state.costSheetFile) fd.append("cost_sheet_file", state.costSheetFile);

  fd.append("category", category || "");
  if (dialect) fd.append("dialect", dialect);

  return fd;
}

/** Wires a file input to show the names of the currently selected file(s) below it. */
function renderFileList(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  if (!input || !list) return;

  input.addEventListener("change", () => {
    list.innerHTML = "";
    Array.from(input.files).forEach((file) => {
      const li = document.createElement("li");
      li.textContent = file.name;
      list.appendChild(li);
    });
  });
}

/** Call once on page load to wire up every file-list display. */
export function initFileListDisplays() {
  renderFileList("input-episode-files", "episode-file-list");
}