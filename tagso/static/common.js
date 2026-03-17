/**
 * Tagsonomy Common JavaScript
 *
 * Uses data attributes for configuration, minimizing JavaScript and following DRY.
 * Convention: use snake_case for data attributes (e.g., data-subject_uri) to match Python API.
 *
 * Data attributes:
 *   [data-delete] - Delete button (reads data-url, data-uri, data-type, data-* for body)
 *   [data-resize-sidebar] - Handle element for resizing adjacent aside (expects aside + handle + section layout)
 */

(() => {
    'use strict';

    // =========================================================================
    // HTML Escaping and Tagged Template
    // =========================================================================

    function esc(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /**
     * Tagged template literal that auto-escapes interpolated values.
     * Usage: html`<p>Error: ${data.error}</p>`
     * For pre-escaped HTML (e.g. from nested html`...`), use html.raw(s).
     */
    function html(strings, ...values) {
        return strings.reduce((acc, s, i) => {
            const v = values[i];
            if (v === undefined) return acc + s;
            if (v && typeof v === 'object' && '__html' in v) return acc + s + v.__html;
            return acc + s + esc(String(v));
        }, '');
    }
    html.raw = (s) => ({ __html: String(s) });
    html.keep = () => ({ __keep: true });
    html.fragment = (frag) => ({ __fragment: frag });

    /**
     * Renders a list by cloning a template for each item and filling slots.
     * items: array of data
     * slotFn: (item) => slots object for fillTemplate
     * Returns a DocumentFragment containing all rendered items.
     */
    function renderList(templateId, items, slotFn) {
        const frag = document.createDocumentFragment();
        const t = document.getElementById(templateId);
        if (!t || t.tagName !== 'TEMPLATE') return frag;
        for (const item of items) {
            const itemFrag = fillTemplate(templateId, slotFn(item));
            if (itemFrag) frag.appendChild(itemFrag);
        }
        return frag;
    }

    /**
     * Clones a template and fills elements with [data-slot="key"].
     * slots: { key: value } - value is set as textContent, or use html.raw(s) for innerHTML.
     * Optional sections: use data-slot-optional="key" - if slots[key] is falsy, the element is removed.
     * For attribute-only slots use data-slot-attr="attrName" (e.g. data-slot-attr="href").
     */
    function fillTemplate(templateId, slots) {
        const t = document.getElementById(templateId);
        if (!t || t.tagName !== 'TEMPLATE') return null;
        const frag = t.content.cloneNode(true);
        for (const [key, value] of Object.entries(slots)) {
            const el = frag.querySelector(`[data-slot="${key}"], [data-slot-optional="${key}"]`);
            if (!el) continue;
            if (value == null || value === '') {
                if (el.hasAttribute('data-slot-optional')) el.remove();
                continue;
            }
            if (value && typeof value === 'object' && '__keep' in value) continue;
            if (value && typeof value === 'object' && '__value' in value && '__label' in value) {
                el.setAttribute('value', String(value.__value));
                el.textContent = String(value.__label);
                continue;
            }
            if (value && typeof value === 'object' && '__fragment' in value) {
                el.appendChild(value.__fragment.cloneNode(true));
                continue;
            }
            if (value && typeof value === 'object' && !('__html' in value) && !('__keep' in value)) {
                for (const [k, v] of Object.entries(value)) {
                    if (v != null && v !== '') el.setAttribute(k, String(v));
                }
                continue;
            }
            const attr = el.getAttribute('data-slot-attr');
            if (attr) el.setAttribute(attr, String(value));
            else if (value && typeof value === 'object' && '__html' in value) {
                el.innerHTML = value.__html;
            } else if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.value = String(value);
            } else {
                el.textContent = String(value);
            }
        }
        frag.querySelectorAll('[data-slot-optional]').forEach((el) => {
            const key = el.getAttribute('data-slot-optional');
            if (key in slots && (slots[key] == null || slots[key] === '')) el.remove();
        });
        return frag;
    }

    window.esc = esc;
    window.html = html;
    window.fillTemplate = fillTemplate;
    window.renderList = renderList;

    // =========================================================================
    // Delete Operations
    // =========================================================================

    function initDeleteButtons() {
        document.addEventListener('click', e => {
            const btn = e.target.closest('[data-delete]');
            if (!btn) return;

            const url = btn.dataset.url;
            const itemType = btn.dataset.type || 'item';
            
            if (!confirm(`Are you sure you want to delete this ${itemType}?`)) return;

            // Build request body from data-* attributes (excluding url, type, delete)
            // Use snake_case in data attributes: data-subject_uri -> dataset.subject_uri
            const body = {};
            for (const [key, value] of Object.entries(btn.dataset)) {
                if (!['url', 'type', 'delete'].includes(key)) {
                    body[key] = value;
                }
            }

            fetch(url, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            .then(r => r.ok ? location.reload() : Promise.reject())
            .catch(() => alert(`Error deleting ${itemType}`));
        });
    }

    // =========================================================================
    // Resizable Sidebar
    // =========================================================================

    function initResizableSidebar() {
        document.querySelectorAll('[data-resize-sidebar]').forEach(handle => {
            const sidebar = handle.previousElementSibling;
            if (!sidebar || sidebar.tagName !== 'ASIDE') return;

            handle.addEventListener('mousedown', (e) => {
                const startX = e.clientX;
                const startWidth = sidebar.getBoundingClientRect().width;
                const onMove = (ev) => {
                    const dx = ev.clientX - startX;
                    sidebar.style.flexBasis = Math.min(480, Math.max(160, startWidth + dx)) + 'px';
                };
                const onUp = () => {
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                };
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
                e.preventDefault();
            });
        });
    }

    // =========================================================================
    // Initialize on DOM Ready
    // =========================================================================

    document.addEventListener('DOMContentLoaded', () => {
        initDeleteButtons();
        initResizableSidebar();
    });
})();
