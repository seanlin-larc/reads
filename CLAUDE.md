# CLAUDE.md — Reads

Instructions for Claude Code in this repo. Read this file and `README.md` before you change anything.

## What this is

A family web app for book wishlists and library logistics, one tracker for each person: SL, CJ, YC, JY. Static pages on GitHub Pages (https://seanlin-larc.github.io/reads/), Firebase project `family-reading-f4748` for sign-in and (later) data. The owner is Sean. He is not a professional programmer: keep code simple, readable and easy to maintain. No build step, no framework, no bundler. Plain HTML, CSS and ES modules.

## Status (2026-10-22)

- Live (merged to `main` 2026-10-19): sign-in page (`index.html`), reader list (`readers/`), wishlist (`tracker/?reader=CODE`), Reading History (`history/?reader=CODE`). Also on `main`: Firestore rules (`firebase/firestore.rules`, tested in the emulator, published by Sean 2026-10-19), import script (`tools/import_wishlist.py`).
- Firebase: Email/Password with four accounts `sl@`, `cj@`, `yc@`, `jy@family-reading.invalid` (PIN = password). Sign-up and delete are off. Firestore `(default)` exists in `us-west1`. Rules from `firebase/firestore.rules` published by Sean (2026-10-19; again with `logNo` 2026-10-20). Import account `import@family-reading.invalid` created by Sean (2026-10-19). API key Websites restriction: `https://seanlin-larc.github.io/*`, `http://localhost:8000/*`.
- First import done (2026-10-19): 20 YC books from `toWebWishList.md` are in Firestore (1 `Reading`, 2 `EBook`, 12 `Hold`, 5 `None`). `READS_IMPORT_PASSWORD` works.
- Second import done (2026-10-21, Sean asked): 6 YC books from `toWebWishList.md` (1 `Reading`, 5 `None`). Claude first fixed three title spellings and added series data in the file (`notes-with-llm` `main`, commit `2a608bc`).
- Third import done (2026-10-22, Sean asked): 15 YC books from `toWebWishList.md` (Magisterium #2–#5, Alex Rider #3–#13; 2 `Hold`, 13 `None`). Sean chose to leave out Alex Rider #1 and #2: they are `Finished` in Reading History (log #55, #56). Sean fixed these two books in the Firebase console (2026-10-22): series `Alex Rider` #1 and #2, title *Point Blanc*. Claude checked them (2026-10-22). The rules do not let any account change a title or series.
- Sean tested on the live site with a real sign-in (2026-10-22): sign-in, the wishlist and Reading History work.
- Wish List title and Export (2026-10-20, branch `claude/zen-davinci-06pl0h`; Export card on branch `claude/compassionate-hopper-w12ty4`, which also has the `zen-davinci` commit): the wishlist page title is now "YC’s Wish List". The Wish List and Reading History pages each have an "Export" button. It opens a card with two file formats: Markdown (a table, same format as `toWebWishList.md` / `toWebHistory.md`) and JSON. Merged to `main` (Sean asked, 2026-10-20). Sean tested the card and both downloads on the iPhone (2026-10-22): they work.
- Reading History import (2026-10-20, branch `claude/sharp-pascal-sjrlna`): 81 YC books from the Grade 6 log, in `notes-with-llm/projects/yc-reading/toWebHistory.md`. New optional field `logNo` keeps the order of the old log (no dates). Sean published the changed rules (2026-10-20). Sean: *The Chalice of the Gods* is finished (2026-10-13); remove the second *Criminal Destiny*. Import done (2026-10-20): 81 `Finished` books, `logNo` 1 to 81. Merged to `main` (Sean asked, 2026-10-20).

## Decisions (Sean)

- Everyone (SL, CJ, YC, JY) can edit every tracker and wishlist. (2026-10-18)
- `EBook` is an availability status: only an ebook is available in the library. (2026-10-18; spelling `EBook` confirmed 2026-10-19)
- Each person's page shows the wishlist, with a button that links to that person's reading history (log). The button is named "Reading History". (2026-10-18, name 2026-10-19)
- Wishlist display, status values and data model: decided (2026-10-19). Details: `docs/2026-10-19_data-model-and-wishlist-options.md`. Mockup: `docs/mockups/wishlist.html`.
  - Option C: a list. Each book shows only the title, series and number, author(s), and a status button that opens the status flipper.
  - Status values: `None`, `Hold`, `EBook`, `Reading`, `Finished`. Wishlist order: `Hold`, `EBook`, `None`, then `Reading` at the bottom. "Reading" and "Finished" ask for one more confirmation. A "Finished" book leaves the wishlist and goes to Reading History.
  - No loan dates (no ready, due or return date). Only `readOn` (set at "Reading") and `finishedOn` (set at "Finished").
  - The page manages the wishlist and Reading History only. Recommendations stay in LLM chats and `notes-with-llm/projects/yc-reading`. No `Declined` rows.
  - Add books: Sean writes `notes-with-llm/projects/yc-reading/toWebWishList.md`. The file has no Reader column; the script takes the reader from the folder name (`yc-reading` → YC, Sean 2026-10-19). When Sean asks, Claude runs `python tools/import_wishlist.py <file>` (dry run), shows the result, then runs it with `--write` after Sean agrees.
  - Page title: "YC’s Wish List" (Sean, 2026-10-20). Export button on the Wish List and Reading History pages (Sean, 2026-10-20). Export file formats: Markdown and JSON; the Export button opens a card with these two choices (Sean, 2026-10-20). The Markdown columns (import format) and the JSON fields: chosen by Claude.
  - Not needed for now: remove a book, edit a book, move a finished book back to the wishlist.
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
- Every page loads `shared/stuck.js` (a classic script) in `<head>` and has `<p id="loading">`. The page module sets `window.rdStarted = true;` right after its `import` lines. Then, if the module does not start (for example, the browser keeps an old copy of a shared file for up to 10 minutes after a change), the page shows "The page did not load. Reload the page." instead of "Loading…".
- Device storage keys start with `rd-` and are listed in `README.md`.
- Keep `README.md` in step with the code (status table, folder structure, keys).

## Tests

- `python tests/run.py` (see `tests/README.md`). It must pass before every commit. Add checks for every change.
- When `firebase/firestore.rules` or `tools/import_wishlist.py` changes, also run `tests/rules_test.py` with the emulators (command in `tests/README.md`).
- Never type or print `READS_IMPORT_PASSWORD`. The import script reads it from the environment.
- The cloud environment may block `www.gstatic.com`; the tests do not need it, because they use the fake modules in `tests/fake/`.

## Writing and commits

- Write docs, comments and messages to Sean close to ASD-STE100 Simplified Technical English: short sentences, active voice, one term for one meaning, no idioms.
- Start every commit message with `Claude:`, for example `Claude: add wishlist data model`.
- When a decision or a status changes, also update the handoff notes in `seanlin-larc/notes-with-llm`, `projects/reading-tracker/`, if that repo is available in the session.
