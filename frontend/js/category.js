/* =========================================================
   category.js — Family / Young Adult / Dialect-region
   selector, and the free-text dialect field that appears
   when Dialect-region is chosen. The dialect is typed by
   the user; there is no fixed list.
   ========================================================= */

const WRAPPER_ID = "dialect-dropdown-wrapper";
const INPUT_ID = "dialect-input";
const DIALECT_VALUE = "dialect_region";

/** Wires show/hide behavior for the dialect field. */
export function initCategorySelector() {
  const radios = document.querySelectorAll('input[name="category"]');
  const wrapper = document.getElementById(WRAPPER_ID);

  if (!radios.length || !wrapper) return;

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      wrapper.hidden = radio.value !== DIALECT_VALUE;
      if (!wrapper.hidden) document.getElementById(INPUT_ID)?.focus();
    });
  });

  const checked = document.querySelector('input[name="category"]:checked');
  wrapper.hidden = !(checked && checked.value === DIALECT_VALUE);
}

export function getSelectedCategory() {
  const checked = document.querySelector('input[name="category"]:checked');
  return checked ? checked.value : null;
}

/** The dialect the user typed, or null if the field is hidden or empty. */
export function getSelectedDialect() {
  const wrapper = document.getElementById(WRAPPER_ID);
  const input = document.getElementById(INPUT_ID);
  if (!wrapper || !input || wrapper.hidden) return null;
  return input.value.trim() || null;
}