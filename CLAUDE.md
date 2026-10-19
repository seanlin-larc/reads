# CLAUDE.md — Reads

Instructions for Claude Code in this repo. Read this file and `README.md` before you change anything.

## What this is

A family web app for book wishlists and library logistics, one tracker for each person: SL, CJ, YC, JY. Static pages on GitHub Pages (https://seanlin-larc.github.io/reads/), Firebase project `family-reading-f4748` for sign-in and (later) data. The owner is Sean. He is not a professional programmer: keep code simple, readable and easy to maintain. No build step, no framework, no bundler. Plain HTML, CSS and ES modules.

## Status (2026-10-18)

- Live: sign-in page (`index.html`), reader list (`readers/`), tracker placeholder (`tracker/?reader=CODE`).
- Firebase: Email/Password with four accounts `sl@`, `cj@`, `yc@`, `jy@family-reading.invalid` (PIN = password). Sign-up and delete are off. Firestore `(default)` exists in `us-west1`, empty, no rules from us yet. API key Websites restriction: `https://seanlin-larc.github.io/*`, `http://localhost:8000/*`.
- Not built: the tracker (wishlist and reading log), Firestore data model, Firestore rules.

## Decisions (Sean)

- Everyone (SL, CJ, YC, JY) can edit every tracker and wishlist. (2026-10-18)
- `EBook` is an availability status: only an ebook is available in the library. (2026-10-18)
- Each person's page shows the wishlist, with a button that links to that person's reading history (log). (2026-10-18)
- **Not decided:** how the wishlist is displayed, and how status is shown and changed. Do not build this UI until Sean decides. Ask him, and offer mockups or options first. Claude's proposal (data model and options A, B, C): `docs/2026-10-19_data-model-and-wishlist-options.md`.
- Separate Firebase project from Kids Games, no Guest account. (2026-10-18)
- The wishlist intentionally has no "reason for the recommendation" field. Books not chosen from a recommendation list are not "rejected"; they may fit another time. (2026-10-16)

## Why the app exists (Sean, 2026-10-16)

Sean finds book recommendations with LLMs, then reviews them with YC. Chosen books go on the wishlist. After that, the work is library logistics: physical or ebook availability, holds, books on loan, wait times, series order (book 3 must not arrive before books 1 and 2), and borrowing that matches the reader's speed, including return time. Status changes must be fast on an iPhone in the library, with no LLM in the loop. Library: Burnaby Public Library (28-day loans, up to 2 automatic renewals, no renewal when another person has a hold). Details and open proposals: `projects/reading-tracker/` in the private repo `seanlin-larc/notes-with-llm`.

## Hard rules

- **This repo is public.** Never commit a PIN, password, service account key, token, or a real person's name or personal details. Use the codes SL, CJ, YC, JY only.
- **Never type or ask for a real PIN.** Sean tests real sign-in himself.
- **Firestore rules:** write them in `firebase/firestore.rules` and test them with the Firestore emulator. **Sean publishes rules in the Firebase console.** Do not deploy rules or anything else to Firebase. Planned rule: allow read and write only when `request.auth.token.email` is one of the four emails.
- Do not change Firebase or Google Cloud settings. Tell Sean what to change and why.
- Push to `main` only when Sean asks. Otherwise work on a branch. GitHub Pages serves `main` / `(root)`, so `main` is the live site.

## Code rules

- Relative links only (`href="readers/"`, never `href="/readers/"`); the site is under `/reads/`.
- Firebase web SDK 13.0.0 from `https://www.gstatic.com/firebasejs/13.0.0/`. All Firebase code goes through `shared/auth.js`; pages load it through `shared/load.js`.
- Phone first: test at 390 px wide, light and dark. Tap targets at least 44 px.
- Device storage keys start with `rd-` and are listed in `README.md`.
- Keep `README.md` in step with the code (status table, folder structure, keys).

## Tests

- `python tests/run.py` (see `tests/README.md`). It must pass before every commit. Add checks for every change.
- The cloud environment may block `www.gstatic.com`; the tests do not need it, because they use the fake modules in `tests/fake/`.

## Writing and commits

- Write docs, comments and messages to Sean close to ASD-STE100 Simplified Technical English: short sentences, active voice, one term for one meaning, no idioms.
- Start every commit message with `Claude:`, for example `Claude: add wishlist data model`.
- When a decision or a status changes, also update the handoff notes in `seanlin-larc/notes-with-llm`, `projects/reading-tracker/`, if that repo is available in the session.
