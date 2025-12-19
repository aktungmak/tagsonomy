/**
 * Tagsonomy Common JavaScript
 * 
 * Uses data attributes for configuration, minimizing JavaScript and following DRY.
 * Convention: use snake_case for data attributes (e.g., data-subject_uri) to match Python API.
 * 
 * Data attributes:
 *   [data-filter-for="list_id"] - Search input that filters a list
 *   [data-delete]               - Delete button (reads data-url, data-uri, data-type, data-* for body)
 *   [data-uri-from="input_ids"] - URI input auto-generated from other inputs (comma-separated IDs)
 *   [data-user-ns]              - User namespace for URI generation
 *   [data-cascade]              - Cascade select (reads data-resets, data-enables)
 *   [data-add-alt-label="id"]   - Button to add alt label field to container
 *   [data-remove-field]         - Button to remove its parent .alt-label-field
 */

(() => {
    'use strict';

    // =========================================================================
    // List Filtering
    // =========================================================================

    function initFiltering() {
        document.querySelectorAll('[data-filter-for]').forEach(input => {
            const listId = input.dataset.filterFor;
            const list = document.getElementById(listId);
            if (!list) return;

            const filter = () => {
                const query = input.value.toUpperCase();
                Array.from(list.children).forEach(item => {
                    const searchable = item.querySelector('[data-searchable]') 
                        ? Array.from(item.querySelectorAll('[data-searchable]'))
                        : Array.from(item.querySelectorAll('span'));
                    const text = searchable.map(el => el.textContent).join(' ').toUpperCase();
                    item.hidden = !text.includes(query);
                });
            };

            input.addEventListener('input', filter);
            // Apply initial filter if input has a value
            if (input.value) filter();
        });
    }

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
    // URI Generation
    // =========================================================================

    function initUriGeneration() {
        document.querySelectorAll('[data-uri-from]').forEach(uriInput => {
            const sourceIds = uriInput.dataset.uriFrom.split(',').map(s => s.trim());
            const nsElement = document.querySelector('[data-user-ns]');
            const userNs = nsElement?.dataset.userNs || '';
            const separator = uriInput.dataset.uriSeparator || '.';

            const updateUri = () => {
                const parts = sourceIds
                    .map(id => document.getElementById(id)?.value)
                    .filter(Boolean);
                
                if (parts.length === sourceIds.length && parts.every(Boolean)) {
                    uriInput.value = userNs + encodeURIComponent(parts.join(separator));
                }
            };

            sourceIds.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.addEventListener('input', updateUri);
            });
        });
    }

    // =========================================================================
    // Alternative Labels (Dynamic Fields)
    // =========================================================================

    function createAltLabelField() {
        const div = document.createElement('div');
        div.className = 'alt-label-field';
        div.innerHTML = `
            <input type="text" name="alt_labels" placeholder="Alternative label" required>
            <button type="button" data-remove-field>Remove</button>
        `;
        return div;
    }

    function initAltLabels() {
        // Add button handling
        document.addEventListener('click', e => {
            const addBtn = e.target.closest('[data-add-alt-label]');
            if (addBtn) {
                const containerId = addBtn.dataset.addAltLabel;
                const container = document.getElementById(containerId);
                if (container) container.appendChild(createAltLabelField());
                return;
            }

            // Remove button handling
            const removeBtn = e.target.closest('[data-remove-field]');
            if (removeBtn) {
                removeBtn.closest('.alt-label-field')?.remove();
            }
        });
    }

    // =========================================================================
    // Cascade Selects (for Tables/Columns)
    // =========================================================================

    function initCascadeSelects() {
        document.querySelectorAll('[data-cascade]').forEach(select => {
            select.addEventListener('change', async () => {
                const apiPath = select.dataset.cascade;
                const resets = (select.dataset.resets || '').split(',').filter(Boolean);
                const enables = select.dataset.enables;
                const targetSelect = enables ? document.getElementById(enables) : null;

                // Reset dependent selects
                resets.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.innerHTML = `<option value="">Select ${id}...</option>`;
                        el.disabled = true;
                    }
                });

                // Update URI if applicable
                document.querySelectorAll('[data-uri-from]').forEach(el => el.dispatchEvent(new Event('recalculate')));

                if (!select.value || !targetSelect) return;

                // Build API URL from path segments
                const pathParts = apiPath.split('/').map(part => {
                    if (part.startsWith(':')) {
                        const id = part.slice(1);
                        return document.getElementById(id)?.value || '';
                    }
                    return part;
                });
                const url = pathParts.join('/');

                targetSelect.innerHTML = '<option value="">Loading...</option>';
                
                try {
                    const items = await fetch(url).then(r => r.json());
                    targetSelect.innerHTML = `<option value="">Select ${enables}...</option>` +
                        items.map(item => `<option value="${item}">${item}</option>`).join('');
                    targetSelect.disabled = false;
                } catch {
                    targetSelect.innerHTML = '<option value="">Error loading</option>';
                }
            });
        });
    }

    // =========================================================================
    // Initialize on DOM Ready
    // =========================================================================

    document.addEventListener('DOMContentLoaded', () => {
        initFiltering();
        initDeleteButtons();
        initUriGeneration();
        initAltLabels();
        initCascadeSelects();
    });
})();
