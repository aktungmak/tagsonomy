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
   * Renders icon markup if DuboisIcons is available and icon name is given.
   * @param {string} [iconName] - Name from DuboisIcons (catalog, schema, table, column, book, group, lightbulb, link)
   */
  function renderIcon(iconName) {
    if (!iconName || typeof DuboisIcons === 'undefined') return '';
    const svg = DuboisIcons.get(iconName);
    return svg ? `<span class="tree-icon">${svg}</span>` : '';
  }

  /**
   * Renders an expandable tree item (caret + nested ul).
   * @param {string} id - Unique id for the nested ul
   * @param {string} label - Display text
   * @param {Record<string, string>} dataAttrs - Data attributes for the caret span
   * @param {string} [icon] - DuBois icon name (catalog, schema, table, book, etc.)
   */
  function renderExpandable(id, label, dataAttrs, icon) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    const iconHtml = renderIcon(icon);
    return `<li>
  <span class="caret" data-controls="${esc(id)}" ${attrs}>${iconHtml}${esc(label)}</span>
  <ul class="nested" id="${esc(id)}"></ul>
</li>`;
  }

  /**
   * Renders a leaf tree item.
   * @param {string} label - Display text
   * @param {Record<string, string>} dataAttrs - Data attributes for the li
   * @param {string} [icon] - DuBois icon name
   */
  function renderLeaf(label, dataAttrs, icon) {
    const attrs = Object.entries(dataAttrs || {})
      .map(([k, v]) => `${toDataAttr(k)}="${esc(v)}"`)
      .join(' ');
    const extra = attrs ? ` ${attrs}` : '';
    const iconHtml = renderIcon(icon);
    return `<li class="tree-leaf"${extra}><span class="tree-leaf-content">${iconHtml}${esc(label)}</span></li>`;
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

  /**
   * Expands a caret node, loads children, renders them, and attaches handlers.
   * @param {Element} caret - The caret span element
   * @param {Object} config - Configuration object
   * @param {function(Element): Promise<Array>} config.loadChildren - Async loader returning child items
   * @param {function(Array, string, Element): string} config.renderChildren - Renders children HTML; receives (children, subtreeId, parentCaret)
   * @param {function(Element): void} [config.afterExpand] - Called after expand (e.g. select parent)
   * @param {function(Element): void} [config.onLeafSelect] - Called when a leaf is clicked
   */
  async function expandAndAttach(caret, config) {
    const subtreeId = caret.getAttribute('data-controls');
    const subtree = subtreeId ? document.getElementById(subtreeId) : null;
    if (!subtree) return;

    if (isExpanded(caret)) {
      toggle(caret);
      return;
    }

    const children = await config.loadChildren(caret);
    subtree.innerHTML = config.renderChildren(children, subtreeId, caret);

    subtree.querySelectorAll('.caret').forEach((c) => {
      c.addEventListener('click', async (e) => {
        e.stopPropagation();
        await expandAndAttach(c, config);
        if (config.afterExpand) config.afterExpand(c);
      });
    });
    subtree.querySelectorAll('li.tree-leaf').forEach((li) => {
      li.addEventListener('click', () => {
        if (config.onLeafSelect) config.onLeafSelect(li);
      });
    });

    toggle(caret);
    if (config.afterExpand) config.afterExpand(caret);
  }

  /**
   * Attaches click handler to a caret that expands and loads children.
   * Use for root-level carets; child carets are attached inside expandAndAttach.
   */
  function setupCaret(caret, config) {
    caret.addEventListener('click', async (e) => {
      e.stopPropagation();
      await expandAndAttach(caret, config);
    });
  }

  return { esc, renderExpandable, renderLeaf, toggle, isExpanded, expandAndAttach, setupCaret };
})();
