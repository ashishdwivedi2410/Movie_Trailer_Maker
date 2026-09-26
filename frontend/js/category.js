/* =========================================================
   category.js — Family / Young Adult / Dialect-region
   selector, and the dialect dropdown that appears when
   Dialect-region is chosen.
   ========================================================= */

import { fetchDialects } from "./api.js";

const WRAPPER_ID = "dialect-dropdown-wrapper";
const SELECT_ID = "dialect-select";
const DIALECT_VALUE = "dialect_region";

/** Populates the dialect dropdown and wires show/hide behavior. */
export async function initCategorySelector() {
  const radios = document.querySelectorAll('input[name="category"]');
  const wrapper = document.getElementById(WRAPPER_ID);
  const select = document.getElementById(SELECT_ID);

  if (!radios.length || !wrapper || !select) return;

  try {
    const dialects = await fetchDialects();
    select.innerHTML = "";
    dialects.forEach((dialect) => {
      const option = document.createElement("option");
      option.value = dialect;
      option.textContent = dialect;
      select.appendChild(option);
    });
  } catch (err) {
    // Leave whatever placeholder options are already in the markup
  }

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      wrapper.hidden = radio.value !== DIALECT_VALUE;
    });
  });

  const checked = document.querySelector('input[name="category"]:checked');
  wrapper.hidden = !(checked && checked.value === DIALECT_VALUE);
}

export function getSelectedCategory() {
  const checked = document.querySelector('input[name="category"]:checked');
  return checked ? checked.value : null;
}

export function getSelectedDialect() {
  const wrapper = document.getElementById(WRAPPER_ID);
  const select = document.getElementById(SELECT_ID);
  if (!wrapper || !select || wrapper.hidden) return null;
  return select.value || null;
}