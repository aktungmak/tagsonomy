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
   * Renders an expandable tree item.
   * @param {string} id - Unique id for the subtree ul (e.g. "scheme-subtree-0")
   * @param {string} label - Button label text
   * @param {Record<string, string>} dataAttrs - Data attributes for the button (e.g. { scheme_uri: "..." })
   */
  function renderExpandable(id, label, dataAttrs) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    return `<li class="tree-node">
  <button type="button" class="tree-toggle" ${attrs} aria-expanded="false" aria-controls="${esc(id)}">
    ${esc(label)}
  </button>
  <ul id="${esc(id)}" class="tree-children" hidden></ul>
</li>`;
  }

  /**
   * Renders a leaf tree item.
   * @param {string} label - Text content
   * @param {Record<string, string>} dataAttrs - Data attributes for the li
   */
  function renderLeaf(label, dataAttrs) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    return attrs ? `<li ${attrs}>${esc(label)}</li>` : `<li>${esc(label)}</li>`;
  }

  return { esc, renderExpandable, renderLeaf };
})();
