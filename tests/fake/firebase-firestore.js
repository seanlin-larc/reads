// Fake Firestore for tests. Books are kept in localStorage 'fake-db':
//   { "readers/YC/books": { "<id>": { title, status, ... } } }
// Each updateDoc is also added to localStorage 'fake-writes'. If localStorage 'fake-db-error'
// is set, onSnapshot fails with that error code (for example 'permission-denied').
const DB = 'fake-db';
const listeners = [];
const load = () => JSON.parse(localStorage.getItem(DB) || '{}');
const save = d => localStorage.setItem(DB, JSON.stringify(d));

export function persistentMultipleTabManager() { return {}; }
export function persistentLocalCache(o) { return { o }; }
export function initializeFirestore(app) {
  if (!app || !app.c || app.c.projectId !== 'family-reading-f4748') throw new Error('wrong project config');
  return { app };
}
export function getFirestore(app) { return initializeFirestore(app); }
export function collection(db, ...path) { return { path: path.join('/') }; }
export function doc(db, ...path) { return { path: path.join('/') }; }
export function serverTimestamp() { return { fakeServerTime: true }; }

function emit(l) {
  const err = localStorage.getItem('fake-db-error');
  if (err) { l.error && l.error(Object.assign(new Error(err), { code: err })); return; }
  const books = load()[l.path] || {};
  l.next({ docs: Object.entries(books).map(([id, data]) => ({ id, data: () => data })) });
}
export function onSnapshot(ref, next, error) {
  const l = { path: ref.path, next, error };
  listeners.push(l);
  setTimeout(() => emit(l), 0);
  return () => listeners.splice(listeners.indexOf(l), 1);
}
export async function updateDoc(ref, fields) {
  const i = ref.path.lastIndexOf('/');
  const col = ref.path.slice(0, i), id = ref.path.slice(i + 1);
  const d = load();
  if (!d[col] || !d[col][id]) throw Object.assign(new Error('not found'), { code: 'not-found' });
  Object.assign(d[col][id], fields);
  save(d);
  const w = JSON.parse(localStorage.getItem('fake-writes') || '[]');
  w.push({ path: ref.path, fields });
  localStorage.setItem('fake-writes', JSON.stringify(w));
  listeners.filter(l => l.path === col).forEach(emit);
}
