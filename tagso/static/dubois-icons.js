/**
 * DuBois icon SVGs for use in tree views.
 * Source: https://github.com/evasnee-db/db-starter-kit/tree/main/src/components/icons
 * 16×16 viewBox, currentColor for theming.
 */
const DuboisIcons = (function () {
  'use strict';

  const base = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" class="tree-icon-svg" aria-hidden="true">';

  const catalog =
    base +
    '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M14 .75a.75.75 0 0 0-.75-.75H4.5A2.5 2.5 0 0 0 2 2.5v10.75A2.75 2.75 0 0 0 4.75 16h8.5a.75.75 0 0 0 .75-.75zM3.5 4.792v8.458c0 .69.56 1.25 1.25 1.25h7.75V5h-8c-.356 0-.694-.074-1-.208m9-1.292v-2h-8a1 1 0 0 0 0 2z"/></svg>';

  const schema =
    base +
    '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2.75 0A.75.75 0 0 0 2 .75v3a.75.75 0 0 0 .75.75h1v7a2.75 2.75 0 0 0 2.75 2.75H7v1c0 .414.336.75.75.75h5.5a.75.75 0 0 0 .75-.75v-3a.75.75 0 0 0-.75-.75h-5.5a.75.75 0 0 0-.75.75v.5h-.5c-.69 0-1.25-.56-1.25-1.25V8.45c.375.192.8.3 1.25.3H7v.75c0 .414.336.75.75.75h5.5A.75.75 0 0 0 14 9.5v-3a.75.75 0 0 0-.75-.75h-5.5A.75.75 0 0 0 7 6.5v.75h-.5c-.69 0-1.25-.56-1.25-1.25V4.5h8a.75.75 0 0 0 .75-.75v-3a.75.75 0 0 0-.75-.75zm.75 3V1.5h9V3zm5 10v1.5h4V13zm0-4.25v-1.5h4v1.5z"/></svg>';

  const table =
    base +
    '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M1 1.75A.75.75 0 0 1 1.75 1h12.5a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75H1.75a.75.75 0 0 1-.75-.75zm1.5.75v3h11v-3zm0 11V7H5v6.5zm4 0h3V7h-3zM11 7v6.5h2.5V7z"/></svg>';

  const column =
    base +
    '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M6.5 9V6h3v3zm3 1.5v3h-3v-3zm1.5-.75v-9a.75.75 0 0 0-.75-.75h-4.5A.75.75 0 0 0 5 .75v13.5c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75zM6.5 4.5v-3h3v3z"/></svg>';

  const book =
    base +
    '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2.75 1a.75.75 0 0 0-.75.75v13.5c0 .414.336.75.75.75h10.5a.75.75 0 0 0 .75-.75V1.75a.75.75 0 0 0-.75-.75zM7.5 2.5h-4v6.055l1.495-1.36a.75.75 0 0 1 1.01 0L7.5 8.555zm-4 8.082 2-1.818 2.246 2.041A.75.75 0 0 0 9 10.25V2.5h3.5v12h-9z"/></svg>';

  const group =
    base +
    '<path fill="currentColor" d="M2.5 13.5H4V15H1.75a.75.75 0 0 1-.75-.75V12h1.5zM10 15H6v-1.5h4zM15 14.25a.75.75 0 0 1-.75.75H12v-1.5h1.5V12H15z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M8.75 6.5a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-.75.75h-4a.75.75 0 0 1-.75-.75v-4a.75.75 0 0 1 .75-.75zm-3.25 4H8V8H5.5z"/><path fill="currentColor" d="M2.5 10H1V6h1.5zM15 10h-1.5V6H15zM11.25 4a.75.75 0 0 1 .75.75V9h-1.5V5.5H7V4zM4 2.5H2.5V4H1V1.75A.75.75 0 0 1 1.75 1H4zM14.25 1a.75.75 0 0 1 .75.75V4h-1.5V2.5H12V1zM10 2.5H6V1h4z"/></svg>';

  const lightbulb =
    base +
    '<path fill="currentColor" d="M7.25 0v2h1.5V0zM16 7.25h-2v1.5h2zM0 7.25h2v1.5H0zM13.127 1.813l-1.415 1.414 1.061 1.06 1.414-1.414zM2.874 1.813l1.414 1.414-1.06 1.06-1.415-1.414z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M3.25 8.221C3.25 5.61 5.382 3.5 8 3.5s4.75 2.109 4.75 4.721a4.7 4.7 0 0 1-.985 2.879c-.754.973-1.33 1.776-1.33 2.644v1.506a.75.75 0 0 1-.75.75h-3.37a.75.75 0 0 1-.75-.75v-1.506c0-.868-.576-1.67-1.33-2.644A4.7 4.7 0 0 1 3.25 8.22M8 5C6.2 5 4.75 6.447 4.75 8.221c0 .738.25 1.417.67 1.96l.044.056c.284.366.612.789.897 1.263h3.278c.285-.474.613-.897.897-1.263l.043-.056c.422-.543.671-1.222.671-1.96C11.25 6.447 9.8 5 8 5m-.934 8.744c0-.256-.03-.504-.081-.744h2.03q-.079.36-.08.744v.756h-1.87z"/></svg>';

  const link =
    base +
    '<path fill="currentColor" d="M4 4h3v1.5H4a2.5 2.5 0 0 0 0 5h3V12H4a4 4 0 0 1 0-8M12 10.5H9V12h3a4 4 0 0 0 0-8H9v1.5h3a2.5 2.5 0 0 1 0 5"/><path fill="currentColor" d="M4 8.75h8v-1.5H4z"/></svg>';

  const icons = {
    catalog,
    schema,
    table,
    column,
    book,
    group,
    lightbulb,
    link
  };

  function get(name) {
    return icons[name] || '';
  }

  return { get, catalog, schema, table, column, book, group, lightbulb, link };
})();
