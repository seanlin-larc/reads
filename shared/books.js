// Book lists for the wishlist and Reading History pages. No Firebase code here
// (Firebase is in auth.js). Decisions: docs/2026-10-19_data-model-and-wishlist-options.md.

export const READERS = ['SL', 'CJ', 'YC', 'JY'];

// The five status values (Sean, 2026-10-19). The Firestore rules allow only these.
export const STATUSES = ['None', 'Hold', 'EBook', 'Reading', 'Finished'];
export const HELP = {
  None: 'On the wishlist', Hold: 'Hold placed', EBook: 'Only an ebook',
  Reading: 'Checked out', Finished: 'Finished and returned'
};
// These ask once more before they change. [question, yes-button text]
export const CONFIRM = {
  Reading: ['Checked out?', 'Yes, Reading'],
  Finished: ['Finished and returned? The book moves to Reading History.', 'Yes, Finished']
};
// Wishlist order (Sean, 2026-10-19): Hold, EBook, None, then Reading at the bottom.
const ORDER = ['Hold', 'EBook', 'None', 'Reading'];

// Today on this phone, as text like 2026-10-19.
export function today() {
  return new Date().toLocaleDateString('en-CA');
}

// The reader code from the page address (?reader=YC), or null.
export function readerFromUrl() {
  const r = new URLSearchParams(location.search).get('reader');
  return READERS.includes(r) ? r : null;
}

const byName = (a, b) =>
  (a.series || a.title).localeCompare(b.series || b.title)
  || (a.seriesNo || 0) - (b.seriesNo || 0)
  || a.title.localeCompare(b.title);

// Books on the wishlist: every status except Finished, in the wishlist order,
// then by series (or title) A to Z, then by number in the series.
export function wishlist(books) {
  return books.filter(b => b.status !== 'Finished')
    .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || byName(a, b));
}

// Books in Reading History: Finished, newest first.
// - Books with a finishedOn date come first, newest date first.
// - Then the books from the old reading log (no date): logNo is the place in the old log,
//   1 = finished first. The highest logNo is the newest, so it comes first.
// - Books with no date and no logNo go last.
export function history(books) {
  return books.filter(b => b.status === 'Finished')
    .sort((a, b) => (b.finishedOn || '').localeCompare(a.finishedOn || '')
      || (b.logNo || 0) - (a.logNo || 0) || byName(a, b));
}

function line(cls, text) {
  const d = document.createElement('div');
  d.className = cls;
  d.textContent = text;
  return d;
}

// The text part of a book row: title, "Series · #2", author(s).
export function bookInfo(b) {
  const box = document.createElement('div');
  box.className = 'grow';
  box.append(line('t', b.title));
  if (b.series) box.append(line('m', b.series + (b.seriesNo ? ' · #' + b.seriesNo : '')));
  if (b.author) box.append(line('m', b.author));
  return box;
}

// ---------- export ----------
// Export (Sean, 2026-10-20): the Export button opens a card with two file formats.
// - Markdown: a table in the same format as toWebWishList.md and toWebHistory.md,
//   so tools/import_wishlist.py can read the file again.
// - JSON: the same books and columns, for programs and LLMs.
const CELLS = {
  'Log #': b => b.logNo, Title: b => b.title, Series: b => b.series, '#': b => b.seriesNo,
  'Author(s)': b => b.author, Status: b => b.status, 'Read on': b => b.readOn, 'Finished on': b => b.finishedOn
};
// The JSON name of each column (the Firestore field name).
const KEYS = {
  'Log #': 'logNo', Title: 'title', Series: 'series', '#': 'seriesNo',
  'Author(s)': 'author', Status: 'status', 'Read on': 'readOn', 'Finished on': 'finishedOn'
};
export const WISHLIST_COLUMNS = ['Title', 'Series', '#', 'Author(s)', 'Status', 'Read on'];
export const HISTORY_COLUMNS = ['Log #', 'Title', 'Series', '#', 'Author(s)', 'Status', 'Read on', 'Finished on'];

// The text of the Markdown file: a heading, the date, then one table row for each book.
export function toMarkdown(heading, list, columns) {
  // A "|" in a cell would end the cell, so it becomes "\|". Line breaks become spaces.
  const cell = v => v == null ? '' : String(v).replace(/\s+/g, ' ').replace(/\|/g, '\\|');
  const row = values => '| ' + values.join(' | ') + ' |';
  return ['# ' + heading, '', 'Exported ' + today() + ' from Reads. ' + list.length + (list.length === 1 ? ' book.' : ' books.'), '',
    row(columns), row(columns.map(() => '---')),
    ...list.map(b => row(columns.map(c => cell(CELLS[c](b))))), ''].join('\n');
}

// The text of the JSON file: the heading, the date, the count, then one object for each book.
// Each book has every column of the page; an empty value is null.
export function toJson(heading, list, columns) {
  const books = list.map(b => Object.fromEntries(columns.map(c => {
    const v = CELLS[c](b);
    return [KEYS[c], v == null || v === '' ? null : v];
  })));
  return JSON.stringify({ title: heading, exported: today(), count: list.length, books }, null, 2) + '\n';
}

// Saves the text as a file on this device (iPhone: the Downloads folder in the Files app).
export function download(fileName, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type: type + ';charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// The export card. It opens at the bottom of the screen with two choices, Markdown and JSON.
// fileName has no extension, for example "YC-wish-list-2026-10-20".
export function openExportCard(from, fileName, heading, list, columns) {
  const shade = document.createElement('div');
  shade.className = 'shade';
  const card = document.createElement('div');
  card.className = 'sheet';
  card.id = 'exportCard';
  card.setAttribute('role', 'dialog');
  card.setAttribute('aria-modal', 'true');
  card.setAttribute('aria-labelledby', 'exportTitle');
  const h = document.createElement('h2');
  h.id = 'exportTitle';
  h.textContent = 'Export ' + heading;
  card.append(h, line('m', (list.length === 1 ? '1 book' : list.length + ' books') + '. Choose a file format.'));

  const close = () => {
    document.removeEventListener('keydown', onKey);
    shade.remove();
    card.remove();
    if (document.contains(from)) from.focus();
  };
  const onKey = e => { if (e.key === 'Escape') close(); };
  const flip = document.createElement('div');
  flip.className = 'flip';
  for (const [name, help, ext, type, make] of [
    ['Markdown', 'a table', '.md', 'text/markdown', toMarkdown],
    ['JSON', 'for programs', '.json', 'application/json', toJson]
  ]) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.dataset.format = name;
    const small = document.createElement('small');
    small.textContent = '· ' + help + ' (' + ext + ')';
    btn.append(name + ' ', small);
    btn.addEventListener('click', () => {
      download(fileName + ext, make(heading, list, columns), type);
      close();
    });
    flip.append(btn);
  }
  const no = document.createElement('button');
  no.type = 'button';
  no.className = 'close';
  no.textContent = 'Close';
  no.addEventListener('click', close);
  card.append(flip, no);

  shade.addEventListener('click', close);
  document.addEventListener('keydown', onKey);
  document.body.append(shade, card);
  flip.querySelector('button').focus();
}
