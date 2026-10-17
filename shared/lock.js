// Wrong-PIN lock for Reads. This file has no Firebase code.
//
// 10 wrong PINs in a row lock that person for 30 minutes, on this device only.
// localStorage key "rd-lock": { CODE: { fails } } or { CODE: { fails: 0, at, until } } when locked.
// A user who clears the site data or uses another browser removes it.
// It stops mistakes and casual tries; it is not a hard guard. Firebase checks the PIN.

export const LOCK_FAILS = 10;     // wrong PINs in a row before a lock
export const LOCK_MINUTES = 30;   // length of the lock

const KEY = "rd-lock";

function read() {
  try { const v = JSON.parse(localStorage.getItem(KEY)); return v && typeof v === "object" ? v : {}; }
  catch (e) { return {}; }
}
function write(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }

// Returns { locked, until, left } for one person. "left" = wrong PINs left before the lock.
export function lockState(code) {
  const all = read();
  const s = all[code];
  const now = Date.now();
  if (!s) return { locked: false, until: 0, left: LOCK_FAILS };
  if (s.until) {
    // A device clock that is set back (now < at) keeps the lock.
    if (now < s.until || now < s.at) return { locked: true, until: Math.max(s.until, now + 60000), left: 0 };
    delete all[code];
    write(all);
    return { locked: false, until: 0, left: LOCK_FAILS };
  }
  return { locked: false, until: 0, left: Math.max(0, LOCK_FAILS - (s.fails || 0)) };
}

// Counts one wrong PIN. Returns the new lockState.
export function recordFail(code) {
  const all = read();
  const s = all[code] || { fails: 0 };
  s.fails = (s.fails || 0) + 1;
  if (s.fails >= LOCK_FAILS) {
    const now = Date.now();
    all[code] = { fails: 0, at: now, until: now + LOCK_MINUTES * 60 * 1000 };
  } else {
    all[code] = s;
  }
  write(all);
  return lockState(code);
}

// A correct PIN clears the counter.
export function recordSuccess(code) {
  const all = read();
  if (all[code]) { delete all[code]; write(all); }
}
