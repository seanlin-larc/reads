// Family sign-in (Firebase) for all Reads pages.
//
// How it works:
// - Each person (SL, CJ, YC, JY) has one Firebase Email/Password account,
//   <code>@kidsgames.invalid. These are the Kids Games accounts. The 6-digit PIN is the
//   password. Firebase checks the PIN on its server; no PIN or PIN hash is in this public code.
// - Firebase keeps the sign-in for the whole origin (seanlin-larc.github.io). Kids Games uses
//   the same config, so one sign-in covers both sites.
// - Firestore document players/{uid} holds the player code, for example { code: "SL" }.
//
// Pages do not import this file directly. They use ./load.js, which loads this file with a
// time limit and shows a message when Firebase cannot load.

import { initializeApp } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-app.js";
import {
  getAuth, onAuthStateChanged, signInWithEmailAndPassword, signOut
} from "https://www.gstatic.com/firebasejs/13.0.0/firebase-auth.js";
import {
  getFirestore, doc, getDoc
} from "https://www.gstatic.com/firebasejs/13.0.0/firebase-firestore.js";

// The four people. To add a person: make the account in Firebase Authentication,
// add a players/{uid} document with the code, and add one line here.
export const PLAYERS = [
  { code: "SL", email: "sl@kidsgames.invalid" },
  { code: "CJ", email: "cj@kidsgames.invalid" },
  { code: "YC", email: "yc@kidsgames.invalid" },
  { code: "JY", email: "jy@kidsgames.invalid" }
];

// Web app config of the Kids Games Firebase project. This is not a secret: it only names
// the project. Access is controlled by the Firestore security rules.
const firebaseConfig = {
  apiKey: "AIzaSyAeOHHmomoHuUlMu8vHHv7J_nQgztTmEmQ",
  authDomain: "kidsgame-7a262.firebaseapp.com",
  projectId: "kidsgame-7a262",
  storageBucket: "kidsgame-7a262.firebasestorage.app",
  messagingSenderId: "594803942218",
  appId: "1:594803942218:web:e141e745d88090f79997b3"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
export const db = getFirestore(app);   // for the tracker pages (later)

// Resolves once Firebase has restored any saved sign-in. This needs no network.
const authReady = new Promise(resolve => {
  const stop = onAuthStateChanged(auth, user => { stop(); resolve(user); });
});

let cachedPlayer = null;

// Returns { uid, code } for the signed-in person, or null if nobody is signed in.
// Throws "no-player-record" if the account has no players/{uid} document.
// Throws "not-a-reader" if the code is not one of the four people (for example Guest).
export async function currentPlayer() {
  await authReady;
  const user = auth.currentUser;
  if (!user) return null;
  if (cachedPlayer && cachedPlayer.uid === user.uid) return cachedPlayer;
  let snap;
  try { snap = await getDoc(doc(db, "players", user.uid)); }
  catch (e) {
    // The rules refuse the read when the account has no players/{uid} document,
    // and Firebase refuses a session of a deleted account. Both mean: not a family member.
    if (e && (e.code === "permission-denied" || /^auth\/(user-token-expired|user-not-found|user-disabled|invalid-user-token)$/.test(e.code || ""))) {
      throw new Error("no-player-record");
    }
    throw e;
  }
  const code = snap.exists() ? snap.data().code : null;
  if (typeof code !== "string") throw new Error("no-player-record");
  // A Kids Games account that is not one of the four people here (Guest).
  // The caller does not sign it out, because the sign-in is shared with Kids Games.
  if (!PLAYERS.some(p => p.code === code)) throw new Error("not-a-reader");
  cachedPlayer = { uid: user.uid, code };
  return cachedPlayer;
}

// Signs in with the player code and PIN. Returns { uid, code }.
// Errors keep the Firebase error code in error.code, for example "auth/invalid-credential".
export async function signIn(code, pin) {
  const p = PLAYERS.find(x => x.code === code);
  if (!p) throw Object.assign(new Error("Unknown player"), { code: "app/unknown-player" });
  await authReady;
  cachedPlayer = null;
  await signInWithEmailAndPassword(auth, p.email, pin);
  return currentPlayer();
}

export async function signOutPlayer() {
  cachedPlayer = null;
  await signOut(auth);
}
