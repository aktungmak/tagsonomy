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
