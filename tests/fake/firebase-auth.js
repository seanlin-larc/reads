// Fake Firebase Auth for tests. Test PIN only; not a real PIN.
const KEY = 'fake-auth-user';
const D = '@family-reading.invalid';
const USERS = { ['sl' + D]: 'uid-sl', ['cj' + D]: 'uid-cj', ['yc' + D]: 'uid-yc', ['jy' + D]: 'uid-jy', ['other' + D]: 'uid-other' };
const PIN = '135790';
let A = null;
function load() { const s = localStorage.getItem(KEY); return s ? JSON.parse(s) : null; }
export function getAuth(app) {
  if (!app || !app.c || app.c.projectId !== 'family-reading-f4748') throw new Error('wrong project config');
  if (!A) A = { currentUser: load() };
  return A;
}
export function onAuthStateChanged(a, cb) { setTimeout(() => cb(a.currentUser), 0); return () => {}; }
export async function signInWithEmailAndPassword(a, email, pin) {
  localStorage.setItem('fake-calls', String(+(localStorage.getItem('fake-calls') || 0) + 1));
  if (!USERS[email] || pin !== PIN) { const e = new Error('bad'); e.code = 'auth/invalid-credential'; throw e; }
  a.currentUser = { uid: USERS[email], email };
  localStorage.setItem(KEY, JSON.stringify(a.currentUser));
}
export async function signOut(a) { a.currentUser = null; localStorage.removeItem(KEY); }
