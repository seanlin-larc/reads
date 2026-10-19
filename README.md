# Reads

Family reading trackers: wishlists, library holds and checkouts, for each family member. Static web pages on GitHub Pages, with Firebase for sign-in and (later) the data.

- Site: https://seanlin-larc.github.io/reads/
- Notes and decisions: `projects/reading-tracker/` in the private `notes-with-llm` repo.

## Status (2026-10-18)

| Part | Status |
|---|---|
| Firebase project `family-reading-f4748` | Created (Sean, 2026-10-18). See "Firebase settings" |
| Sign-in page (`index.html`) | Built. Uses the `family-reading` project |
| Reader list, the table of contents (`readers/`) | Built |
| One reader's tracker (`tracker/?reader=YC`) | Placeholder only. Not built |
| Firestore rules for tracker data | Not written |
| GitHub Pages | On (Sean, 2026-10-18). `main` / `(root)` |
| Tests (`tests/run.py`) | 31 of 31 passed (2026-10-18), fake Firebase |

## Folder structure

```
reads/
├── index.html          Sign-in: pick a person, type the PIN
├── readers/index.html  Table of contents: pick whose tracker to open
├── tracker/index.html  One person's tracker (placeholder), for example tracker/?reader=YC
├── shared/
│   ├── auth.js         Firebase: config, sign-in, sign-out, who is signed in
│   ├── load.js         Loads auth.js with a time limit, page guard, signed-in bar (no Firebase)
│   ├── lock.js         Wrong-PIN lock on this device (no Firebase)
│   └── style.css       Shared styles, light and dark
├── tests/              Browser tests with fake Firebase (see tests/README.md)
├── .nojekyll           Tells GitHub Pages not to run Jekyll
├── CLAUDE.md           Instructions for Claude Code
└── README.md
```

## Sign-in

- Reads has its own Firebase project, `family-reading-f4748`. It does not use the Kids Games project. So the sign-in is separate: a sign-in or sign-out on Kids Games does not affect Reads, and the reverse.
- Four Email/Password accounts: `sl@`, `cj@`, `yc@`, `jy@family-reading.invalid`. The 6-digit PIN is the password. Firebase checks the PIN on its server. No PIN or PIN hash is in this public code.
- There is no Guest account.
- The person's code comes from the account email (`sl@family-reading.invalid` → `SL`). There is no `players` collection.
- An account that is not one of the four emails is signed out, and the sign-in page shows.
- **Wrong-PIN lock:** 10 wrong PINs in a row lock that person for 30 minutes, on this device only (`localStorage` key `rd-lock`). This is a check in the page, not a server check.

## Firebase settings (Sean, 2026-10-18)

| Setting | Value |
|---|---|
| Project | `family-reading` (ID `family-reading-f4748`) |
| Authentication | Email/Password on. Four accounts as above. Sign-up and delete turned off (User actions) |
| Firestore | `(default)` database, `us-west1` |
| API key | "Browser key (auto created by Firebase)". Websites restriction: `https://seanlin-larc.github.io/*`, `http://localhost:8000/*` (set 2026-10-18) |
| Security rules | Not written yet. Planned: allow only the four emails above. Sean publishes rules in the console |

- The API key is not a secret. The Firestore rules protect the data.
- The Websites restriction uses the whole site (`/*`), not `/reads/*`. Browsers usually send only the site address, not the page path, to Google's servers, so a path rule could block this site.
- Where to find the restriction: Google Cloud console → APIs & Services → Credentials → the browser key → bottom of the page, "Application restrictions".

## Device storage keys

All keys start with `rd-`: `rd-lock` (wrong-PIN counter), `rd-lastPlayer` (last person picked on this device).

## Local test

Run `python -m http.server 8000` in this folder, then open `http://localhost:8000/`. Opening the files from disk does not work.

## Rules for changes

- Use relative links only (`href="readers/"`), never `href="/readers/"`. The site is under `/reads/`.
- Keep the Firebase SDK version at 13.0.0 unless there is a reason to change it.
- Never put a PIN, password, service account key, or other secret in this repo. The repo is public.
- Put the LLM name first in each commit message, for example `Claude: add tracker page`.
