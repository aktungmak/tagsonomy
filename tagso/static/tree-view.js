/**
 * Shared tree view rendering for consistent display across Catalog and Concept Schemes.
 * Produces identical HTML structure so both pages render with the same spacing and styling.
 */
const TreeView = (function () {
  'use strict';

  function esc(s) {
    if (!s) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function toDataAttr(key) {
    return 'data-' + key.replace(/([A-Z])/g, '-$1').replace(/_/g, '-').toLowerCase();
  }

  /**
   * Renders an expandable tree item (caret + nested ul).
   * @param {string} id - Unique id for the nested ul
   * @param {string} label - Display text
   * @param {Record<string, string>} dataAttrs - Data attributes for the caret span
   */
  function renderExpandable(id, label, dataAttrs) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    return `<li>
  <span class="caret" data-controls="${esc(id)}" ${attrs}>${esc(label)}</span>
  <ul class="nested" id="${esc(id)}"></ul>
</li>`;
  }

  /**
   * Renders a leaf tree item.
   */
  function renderLeaf(label, dataAttrs) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    const extra = attrs ? ` ${attrs}` : '';
    return `<li class="tree-leaf"${extra}>${esc(label)}</li>`;
  }

  /**
   * Toggles caret and nested ul visibility. Returns true if now expanded.
   */
  function toggle(caret) {
    const id = caret.getAttribute('data-controls');
    const nested = id ? document.getElementById(id) : null;
    if (!nested) return false;
    const isExpanded = caret.classList.toggle('caret-down');
    nested.classList.toggle('active', isExpanded);
    return isExpanded;
  }

  function isExpanded(caret) {
    return caret.classList.contains('caret-down');
  }

  return { esc, renderExpandable, renderLeaf, toggle, isExpanded };
})();
