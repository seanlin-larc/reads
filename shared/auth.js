// Family sign-in (Firebase) for all Reads pages.
//
// How it works:
// - Reads has its own Firebase project, family-reading-f4748 (not the Kids Games project).
// - Each person (SL, CJ, YC, JY) has one Firebase Email/Password account,
//   <code>@family-reading.invalid. The 6-digit PIN is the password. Firebase checks the PIN
//   on its server; no PIN or PIN hash is in this public code.
// - The person's code comes from the account email: sl@family-reading.invalid -> SL.
//   There is no players collection. The Firestore rules will allow exactly these four emails.
// - Sign-up and delete are turned off in Firebase Authentication, so nobody can add an
//   account from the browser.
//
// Books (Firestore): readers/{code}/books/{bookId}. See docs/2026-10-19_data-model-and-wishlist-options.md.
// The Firestore SDK loads only when a page asks for books, so the sign-in page stays small.
//
// Pages do not import this file directly. They use ./load.js, which loads this file with a
// time limit and shows a message when Firebase cannot load.

import { initializeApp } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-app.js";
import {
  getAuth, onAuthStateChanged, signInWithEmailAndPassword, signOut
} from "https://www.gstatic.com/firebasejs/13.0.0/firebase-auth.js";

// The four people. To add a person: make the account in Firebase Authentication,
// add one line here, and add the email to the Firestore rules.
export const PLAYERS = [
  { code: "SL", email: "sl@family-reading.invalid" },
  { code: "CJ", email: "cj@family-reading.invalid" },
  { code: "YC", email: "yc@family-reading.invalid" },
  { code: "JY", email: "jy@family-reading.invalid" }
];

// Web app config of the family-reading Firebase project. This is not a secret: it only
// names the project. Access is controlled by the Firestore security rules. The API key has
// a Websites restriction: https://seanlin-larc.github.io/* and http://localhost:8000/*.
const firebaseConfig = {
  apiKey: "AIzaSyDmd5-z2gzfaKzdSM1BLuyw2VS0kjDYdAc",
  authDomain: "family-reading-f4748.firebaseapp.com",
  projectId: "family-reading-f4748",
  storageBucket: "family-reading-f4748.firebasestorage.app",
  messagingSenderId: "675966575076",
  appId: "1:675966575076:web:a5e63068103c33e91e67f1"
};

export const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Resolves once Firebase has restored any saved sign-in. This needs no network.
const authReady = new Promise(resolve => {
  const stop = onAuthStateChanged(auth, user => { stop(); resolve(user); });
});

function playerFor(user) {
  const email = (user.email || "").toLowerCase();
  const p = PLAYERS.find(x => x.email === email);
  return p ? { uid: user.uid, code: p.code } : null;
}

// Returns { uid, code } for the signed-in person, or null if nobody is signed in.
// Throws "not-a-reader" if the account is not one of the four people.
export async function currentPlayer() {
  await authReady;
  const user = auth.currentUser;
  if (!user) return null;
  const player = playerFor(user);
  if (!player) throw new Error("not-a-reader");
  return player;
}

// Signs in with the player code and PIN. Returns { uid, code }.
// Errors keep the Firebase error code in error.code, for example "auth/invalid-credential".
export async function signIn(code, pin) {
  const p = PLAYERS.find(x => x.code === code);
  if (!p) throw Object.assign(new Error("Unknown player"), { code: "app/unknown-player" });
  await authReady;
  await signInWithEmailAndPassword(auth, p.email, pin);
  return currentPlayer();
}

export async function signOutPlayer() {
  await signOut(auth);
}

// ---------- Books (Firestore) ----------

const FIRESTORE_URL = "https://www.gstatic.com/firebasejs/13.0.0/firebase-firestore.js";
let firestore = null;   // { fs: the SDK module, db: the database }

async function books() {
  if (!firestore) {
    const fs = await import(FIRESTORE_URL);
    let db;
    try {
      // Keep a copy on the phone, so the list shows and changes are kept when the library
      // has no signal. The changes go to Firestore when the signal comes back.
      db = fs.initializeFirestore(app, {
        localCache: fs.persistentLocalCache({ tabManager: fs.persistentMultipleTabManager() })
      });
    } catch (e) {
      console.warn("[reads] No offline copy:", e);
      db = fs.getFirestore(app);
    }
    firestore = { fs, db };
  }
  return firestore;
}

// Calls onBooks(list) now and after each change, from any phone. Each item is
// { id, title, author, series, seriesNo, status, readOn, finishedOn }.
// Calls onError(error) when Firestore refuses or fails. Returns a function that stops it.
export async function watchBooks(code, onBooks, onError) {
  const { fs, db } = await books();
  return fs.onSnapshot(fs.collection(db, "readers", code, "books"),
    snap => onBooks(snap.docs.map(d => ({ id: d.id, ...d.data() }))),
    onError);
}

// Changes some fields of one book, for example { status: "Reading", readOn: "2026-10-19" }.
// The list changes at once (from the copy on the phone). The promise resolves when Firestore
// has saved the change, which can be much later when there is no signal.
export async function updateBook(code, id, fields) {
  const { fs, db } = await books();
  const player = await currentPlayer();
  return fs.updateDoc(fs.doc(db, "readers", code, "books", id),
    { ...fields, updatedAt: fs.serverTimestamp(), updatedBy: player.code });
}
