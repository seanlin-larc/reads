// Loads the Firebase sign-in code (./auth.js) with a time limit, guards pages that need a
// signed-in person, and draws the signed-in bar. This file has no Firebase code.
//
// Use in a page below the sign-in page:
//   import { requirePlayer, mountBar } from "../shared/load.js";
//   const ctx = await requirePlayer(document.getElementById("problem"));
//   if (ctx) { mountBar(document.getElementById("who"), ctx); ... ctx.player.code ... }
// requirePlayer sends the page to the sign-in page when nobody is signed in, and returns null.

const AUTH_URL = new URL("./auth.js", import.meta.url).href;
export const SIGNIN_URL = new URL("../", import.meta.url).href;

export function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((_, no) =>
    setTimeout(() => no(Object.assign(new Error("timeout"), { code: "app/timeout" })), ms))]);
}

let authPromise = null;

// Resolves to the auth.js module, or null when Firebase cannot load (no internet, blocked).
export function loadAuth() {
  if (!authPromise) {
    authPromise = withTimeout(import(AUTH_URL), 10000).catch(e => {
      console.warn("[reads] Firebase did not load:", e);
      authPromise = null;              // try again next time
      return null;
    });
  }
  return authPromise;
}

// Finds out who is signed in. Returns { mode, auth, player, error }:
//   mode "online"     signed in, checked with Firebase
//   mode "signed-out" nobody is signed in (or the account is not a family member)
//   mode "offline"    Firebase did not load or did not answer
export async function access() {
  const auth = await loadAuth();
  if (!auth) return { mode: "offline", auth: null };
  try {
    const player = await withTimeout(auth.currentPlayer(), 7000);
    if (!player) return { mode: "signed-out", auth };
    return { mode: "online", auth, player };
  } catch (e) {
    // Guest of Kids Games: not a reader. Keep the Kids Games sign-in; show the sign-in page.
    if (e && e.message === "not-a-reader") return { mode: "signed-out", auth, error: e };
    if (e && e.message === "no-player-record") {
      await auth.signOutPlayer().catch(() => {});
      return { mode: "signed-out", auth, error: e };
    }
    return { mode: "offline", auth, error: e };
  }
}

// For pages that need a signed-in person. Returns { auth, player } or null.
// Signed out: goes to the sign-in page. Offline: shows a message in problemEl.
export async function requirePlayer(problemEl) {
  const st = await access();
  if (st.mode === "online") return { auth: st.auth, player: st.player };
  if (st.mode === "signed-out") { location.replace(SIGNIN_URL); return null; }
  if (problemEl) {
    problemEl.hidden = false;
    problemEl.textContent = "No internet connection. Reads needs internet. Reload the page to try again.";
  }
  return null;
}

// Draws "Signed in as XX  [Sign out]" into el.
export function mountBar(el, ctx) {
  el.textContent = "";
  el.classList.add("rd-bar");
  const who = document.createElement("span");
  who.append("Signed in as ");
  const b = document.createElement("b");
  b.textContent = ctx.player.code;
  who.append(b);
  const out = document.createElement("button");
  out.type = "button";
  out.textContent = "Sign out";
  out.addEventListener("click", async () => {
    out.disabled = true;
    try { await ctx.auth.signOutPlayer(); } catch (e) { console.warn("[reads] Sign-out failed:", e); }
    location.replace(SIGNIN_URL);
  });
  el.append(who, out);
}
