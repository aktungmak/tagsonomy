/**
 * Tagsonomy Common JavaScript
 * 
 * This file contains shared functionality across the application.
 * Template-specific configuration (URLs, namespaces) should be set via
 * window.TAGSO_CONFIG before this script loads.
 * 
 * Example:
 *   <script>
 *     window.TAGSO_CONFIG = {
 *       deleteUrl: '/concepts/delete',
 *       userNs: 'http://example.org/'
 *     };
 *   </script>
 *   <script src="/static/common.js"></script>
 */

// ============================================================================
// Generic List Filtering
// ============================================================================

/**
 * Filter a list by matching search text against elements with specific classes.
 * @param {string} searchInputId - ID of the search input element
 * @param {string} listId - ID of the list container (ul)
 * @param {string} searchableClass - Class name of searchable elements (optional)
 */
function filterList(searchInputId, listId, searchableClass) {
    const input = document.getElementById(searchInputId);
    const filter = input.value.toUpperCase();
    const ul = document.getElementById(listId);
    const li = ul.children;

    for (let i = 0; i < li.length; i++) {
        let txt = '';
        
        if (searchableClass) {
            // Search elements with the specified class
            const spans = li[i].getElementsByClassName(searchableClass);
            for (let j = 0; j < spans.length; j++) {
                txt += spans[j].textContent || spans[j].innerText;
            }
        } else {
            // Fallback: search all spans
            const spans = li[i].getElementsByTagName('span');
            for (let j = 0; j < spans.length; j++) {
                txt += ' ' + (spans[j].textContent || spans[j].innerText);
            }
        }
        
        if (txt.toUpperCase().indexOf(filter) > -1) {
            li[i].style.display = "";
        } else {
            li[i].style.display = "none";
        }
    }
}

// Page-specific filter functions (wrappers for compatibility with existing HTML)
function filter_concepts() {
    filterList('concept_search', 'concept_list');
}

function filter_properties() {
    filterList('property_search', 'property_list');
}

function filter_tables() {
    filterList('table_search', 'table_list', 'searchable');
}

function filter_columns() {
    filterList('column_search', 'column_list', 'searchable');
}

// ============================================================================
// Delete Operations
// ============================================================================

/**
 * Generic delete function that sends a DELETE request
 * @param {string} uri - The URI of the item to delete
 * @param {string} deleteUrl - The endpoint URL for deletion
 * @param {string} itemType - Human-readable item type for error messages
 */
function deleteItem(uri, deleteUrl, itemType) {
    if (confirm(`Are you sure you want to delete this ${itemType}?`)) {
        fetch(deleteUrl, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ uri: uri })
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert(`Error deleting ${itemType}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error deleting ${itemType}`);
        });
    }
}

// Page-specific delete functions using config
function delete_concept(concept_uri) {
    const config = window.TAGSO_CONFIG || {};
    deleteItem(concept_uri, config.conceptDeleteUrl, 'concept');
}

function delete_property(property_uri) {
    const config = window.TAGSO_CONFIG || {};
    deleteItem(property_uri, config.propertyDeleteUrl, 'property');
}

function delete_table(table_uri) {
    const config = window.TAGSO_CONFIG || {};
    deleteItem(table_uri, config.tableDeleteUrl, 'table');
}

function delete_column(column_uri) {
    const config = window.TAGSO_CONFIG || {};
    deleteItem(column_uri, config.columnDeleteUrl, 'column');
}

/**
 * Delete a concept relationship
 */
function delete_relationship(subject_uri, predicate_type, object_uri) {
    const config = window.TAGSO_CONFIG || {};
    if (confirm('Are you sure you want to delete this relationship?')) {
        fetch(config.relationshipDeleteUrl, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subject_uri: subject_uri,
                predicate_type: predicate_type,
                object_uri: object_uri
            })
        })
        .then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                alert('Error deleting relationship');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting relationship');
        });
    }
}

// ============================================================================
// URI Generation
// ============================================================================

/**
 * Get the user namespace from config
 */
function getUserNs() {
    const config = window.TAGSO_CONFIG || {};
    return config.userNs || '';
}

/**
 * Generate a URI from a label using the user namespace
 */
function generate_uri_from_label(label) {
    if (!label) return '';
    return getUserNs() + encodeURIComponent(label);
}

/**
 * Update URI input based on label input (for concept creation)
 */
function update_uri_from_label() {
    const labelInput = document.getElementById('label');
    const uriInput = document.getElementById('uri');
    if (labelInput && uriInput) {
        uriInput.value = generate_uri_from_label(labelInput.value);
    }
}

/**
 * Generate URI from table name components
 */
function generateUriFromTableName(catalog, schema, tableName) {
    if (!catalog || !schema || !tableName) return '';
    const fullName = `${catalog}.${schema}.${tableName}`;
    return getUserNs() + encodeURIComponent(fullName);
}

/**
 * Generate URI from column name components
 */
function generateUriFromColumnName(catalog, schema, table, column) {
    if (!catalog || !schema || !table || !column) return '';
    const fullName = `${catalog}.${schema}.${table}.${column}`;
    return getUserNs() + encodeURIComponent(fullName);
}

/**
 * Update URI input from cascade select values (tables page)
 */
function updateUriFromSelection() {
    const catalog = document.getElementById('catalog')?.value || '';
    const schema = document.getElementById('schema')?.value || '';
    const table = document.getElementById('table')?.value || '';
    const column = document.getElementById('column')?.value || '';
    const uriInput = document.getElementById('uri');
    
    if (uriInput) {
        if (column) {
            uriInput.value = generateUriFromColumnName(catalog, schema, table, column);
        } else {
            uriInput.value = generateUriFromTableName(catalog, schema, table);
        }
    }
}

// ============================================================================
// Alternative Labels (Dynamic Form Fields)
// ============================================================================

/**
 * Add an alternative label input field to a container
 * @param {string} containerId - ID of the container to add the field to (optional, defaults to 'alt_labels_container')
 */
function addAltLabelField(containerId) {
    const container = document.getElementById(containerId || 'alt_labels_container');
    if (!container) return;
    
    const newField = document.createElement('div');
    newField.className = 'alt-label-field';

    const input = document.createElement('input');
    input.type = 'text';
    input.name = 'alt_labels';
    input.placeholder = 'Alternative label';
    input.required = true;

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.textContent = 'Remove';
    removeBtn.onclick = function() { removeAltLabelField(this); };

    newField.appendChild(input);
    newField.appendChild(removeBtn);
    container.appendChild(newField);
}

/**
 * Remove an alternative label field
 * @param {HTMLElement} button - The remove button that was clicked
 */
function removeAltLabelField(button) {
    button.parentElement.remove();
}

// ============================================================================
// Cascade Select (Tables/Columns from Databricks)
// ============================================================================

const SELECT_PLACEHOLDERS = {
    loading: 'Loading...',
    schema: 'Select Schema...',
    table: 'Select Table...',
    column: 'Select Column...'
};

/**
 * Populate a select element with options
 * @param {HTMLSelectElement} selectElement - The select element to populate
 * @param {Array} items - Array of option values
 * @param {string} placeholder - Placeholder text for the first option
 */
function populateSelect(selectElement, items, placeholder) {
    selectElement.replaceChildren();
    selectElement.add(new Option(placeholder, ''));
    for (const item of items) {
        selectElement.add(new Option(item, item));
    }
}

/**
 * Load schemas for a given catalog
 */
async function loadSchemas() {
    const catalog = document.getElementById('catalog').value;
    const schemaSelect = document.getElementById('schema');
    const tableSelect = document.getElementById('table');
    const columnSelect = document.getElementById('column');
    
    // Reset dependent dropdowns
    populateSelect(schemaSelect, [], SELECT_PLACEHOLDERS.loading);
    populateSelect(tableSelect, [], SELECT_PLACEHOLDERS.table);
    tableSelect.disabled = true;
    
    if (columnSelect) {
        populateSelect(columnSelect, [], SELECT_PLACEHOLDERS.column);
        columnSelect.disabled = true;
    }
    
    updateUriFromSelection();
    
    if (!catalog) {
        populateSelect(schemaSelect, [], SELECT_PLACEHOLDERS.schema);
        schemaSelect.disabled = true;
        return;
    }
    
    const schemas = await fetch(`/api/schemas/${catalog}`).then(r => r.json());
    populateSelect(schemaSelect, schemas, SELECT_PLACEHOLDERS.schema);
    schemaSelect.disabled = false;
}

/**
 * Load tables for a given catalog and schema
 */
async function loadTables() {
    const catalog = document.getElementById('catalog').value;
    const schema = document.getElementById('schema').value;
    const tableSelect = document.getElementById('table');
    const columnSelect = document.getElementById('column');
    
    // Reset column dropdown if it exists
    if (columnSelect) {
        populateSelect(columnSelect, [], SELECT_PLACEHOLDERS.column);
        columnSelect.disabled = true;
    }
    
    if (!schema) {
        populateSelect(tableSelect, [], SELECT_PLACEHOLDERS.table);
        tableSelect.disabled = true;
        updateUriFromSelection();
        return;
    }
    
    populateSelect(tableSelect, [], SELECT_PLACEHOLDERS.loading);
    const tables = await fetch(`/api/tables/${catalog}/${schema}`).then(r => r.json());
    populateSelect(tableSelect, tables, SELECT_PLACEHOLDERS.table);
    tableSelect.disabled = false;
    updateUriFromSelection();
}

/**
 * Load columns for a given catalog, schema, and table
 */
async function loadColumns() {
    const catalog = document.getElementById('catalog').value;
    const schema = document.getElementById('schema').value;
    const table = document.getElementById('table').value;
    const columnSelect = document.getElementById('column');
    
    if (!columnSelect) return;
    
    if (!table) {
        populateSelect(columnSelect, [], SELECT_PLACEHOLDERS.column);
        columnSelect.disabled = true;
        updateUriFromSelection();
        return;
    }
    
    populateSelect(columnSelect, [], SELECT_PLACEHOLDERS.loading);
    const columns = await fetch(`/api/columns/${catalog}/${schema}/${table}`).then(r => r.json());
    populateSelect(columnSelect, columns, SELECT_PLACEHOLDERS.column);
    columnSelect.disabled = false;
    updateUriFromSelection();
}

