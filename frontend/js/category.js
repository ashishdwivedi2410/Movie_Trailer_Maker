/* =========================================================
   category.js — Family / Young Adult / Dialect-region
   selector, and the dialect dropdown that appears when
   Dialect-region is chosen.

   The dialect list comes from the backend. If it cannot be
   loaded the dropdown says so and offers a retry — it never
   falls back to made-up dialects.
   ========================================================= */

import { fetchDialects } from "./api.js";

const WRAPPER_ID = "dialect-dropdown-wrapper";
const SELECT_ID = "dialect-select";
const STATUS_ID = "dialect-status";
const DIALECT_VALUE = "dialect_region";

let dialectsLoaded = false;
let dialectsLoading = false;

function setOptions(select, options) {
  select.innerHTML = "";
  options.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
}

function clearStatus() {
  document.getElementById(STATUS_ID)?.remove();
}

function showLoadError(select, message) {
  clearStatus();
  const status = document.createElement("div");
  status.id = STATUS_ID;
  status.className = "dialect-status";
  status.setAttribute("role", "alert");

  const text = document.createElement("span");
  text.textContent = `Could not load the dialect list. ${message}`;

  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "btn-link";
  retry.textContent = "Retry";
  retry.addEventListener("click", () => loadDialects(select));

  status.append(text, " ", retry);
  select.insertAdjacentElement("afterend", status);
}

async function loadDialects(select) {
  if (dialectsLoading) return;
  dialectsLoading = true;
  clearStatus();
  select.disabled = true;
  setOptions(select, [{ value: "", label: "Loading dialects…" }]);

  try {
    const dialects = await fetchDialects();
    setOptions(select, [
      { value: "", label: "Select a dialect" },
      ...dialects.map((d) => ({ value: d, label: d }))
    ]);
    select.disabled = false;
    dialectsLoaded = true;
  } catch (err) {
    setOptions(select, [{ value: "", label: "Dialects unavailable" }]);
    showLoadError(select, err.message || "");
  } finally {
    dialectsLoading = false;
  }
}

/** Wires show/hide behavior and loads the dialect dropdown. */
export function initCategorySelector() {
  const radios = document.querySelectorAll('input[name="category"]');
  const wrapper = document.getElementById(WRAPPER_ID);
  const select = document.getElementById(SELECT_ID);

  if (!radios.length || !wrapper || !select) return;

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      wrapper.hidden = radio.value !== DIALECT_VALUE;
      // If the first attempt failed (backend was down), try again when the user needs the list.
      if (!wrapper.hidden && !dialectsLoaded) loadDialects(select);
    });
  });

  const checked = document.querySelector('input[name="category"]:checked');
  wrapper.hidden = !(checked && checked.value === DIALECT_VALUE);

  loadDialects(select);
}

export function getSelectedCategory() {
  const checked = document.querySelector('input[name="category"]:checked');
  return checked ? checked.value : null;
}

export function getSelectedDialect() {
  const wrapper = document.getElementById(WRAPPER_ID);
  const select = document.getElementById(SELECT_ID);
  if (!wrapper || !select || wrapper.hidden || select.disabled) return null;
  return select.value || null;
}