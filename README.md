# Reads

Family reading trackers: wishlists, library holds and checkouts, for each family member. Static web pages on GitHub Pages, with Firebase for sign-in and the data (Firestore).

- Site: https://seanlin-larc.github.io/reads/
- Notes and decisions: `projects/reading-tracker/` in the private `notes-with-llm` repo.

## Status (2026-10-20)

| Part | Status |
|---|---|
| Firebase project `family-reading-f4748` | Created (Sean, 2026-10-18). See "Firebase settings" |
| Sign-in page (`index.html`) | Built. Uses the `family-reading` project |
| Reader list, the table of contents (`readers/`) | Built |
| Wishlist (`tracker/?reader=YC`) and Reading History (`history/?reader=YC`) | Built (2026-10-19). Live on `main` (2026-10-19). Design: `docs/2026-10-19_data-model-and-wishlist-options.md`. Old reading log order (`logNo`): live on `main` (2026-10-20) |
| Firestore rules (`firebase/firestore.rules`) | Written and tested in the emulator. Published by Sean (2026-10-19). Change for `logNo` published by Sean (2026-10-20) |
| Import script (`tools/import_wishlist.py`) | Built. Import account made by Sean (2026-10-19). First import done (2026-10-19): 20 YC books. Reading History import done (2026-10-20): 81 YC books from the Grade 6 log |
| GitHub Pages | On (Sean, 2026-10-18). `main` / `(root)` |
| Wish List title ("YC’s Wish List") and Export buttons | Built (2026-10-20), branch `claude/zen-davinci-06pl0h`. Not on `main` yet |
| Tests | `tests/run.py`: 84 of 84 passed (2026-10-20), fake Firebase. `tests/rules_test.py`: 42 of 42 passed (2026-10-20), Firebase emulators |

## Folder structure

```
reads/
├── index.html          Sign-in: pick a person, type the PIN
├── readers/index.html  Table of contents: pick whose tracker to open
├── tracker/index.html  One person's wishlist with the status flipper, for example tracker/?reader=YC
├── history/index.html  One person's Reading History (Finished books), for example history/?reader=YC
├── shared/
│   ├── auth.js         Firebase: config, sign-in, sign-out, who is signed in, books (Firestore)
│   ├── books.js        Status values, list order, book rows and Export for the two book pages (no Firebase)
│   ├── load.js         Loads auth.js with a time limit, page guard, signed-in bar (no Firebase)
│   ├── lock.js         Wrong-PIN lock on this device (no Firebase)
│   └── style.css       Shared styles, light and dark
├── firebase/
│   ├── firestore.rules Firestore rules. Sean publishes them in the Firebase console
│   └── firebase.json   Emulator settings for the rules test (not for deploy)
├── tools/
│   └── import_wishlist.py  Adds books from toWebWishList.md or toWebHistory.md to Firestore (Claude runs it)
├── docs/               Design notes and mockups (not part of the app)
├── tests/              Browser tests with fake Firebase, rules test (see tests/README.md)
├── .nojekyll           Tells GitHub Pages not to run Jekyll
├── .gitignore          Emulator logs and Python cache
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

## Books and import

- Each book is a Firestore document `readers/{code}/books/{bookId}`. Status values: `None`, `Hold`, `EBook`, `Reading`, `Finished`. Details: `docs/2026-10-19_data-model-and-wishlist-options.md`.
- Everyone can change the status of every book. Nobody can add or delete books on the page.
- Reading History order: books with a `finishedOn` date first, newest first. Then the books from the old reading log, which has no dates: the field `logNo` is the place in the old log (1 = finished first), highest first.
- The old reading log comes from `notes-with-llm/projects/yc-reading/toWebHistory.md` (same table format, plus a `Log #` column). From now on, finished books come from the status flipper on the wishlist.
- **Export:** the Wish List and Reading History pages each have an "Export" button. It saves a Markdown file, for example `YC-wish-list-2026-10-20.md` or `YC-reading-history-2026-10-20.md`. The file has a heading, the date, and one table row for each book, in the same order as on the page. The table has the same format as `toWebWishList.md` and `toWebHistory.md`, so `tools/import_wishlist.py` can read it. On an iPhone, the file goes to Downloads in the Files app.
- New books come from `notes-with-llm/projects/yc-reading/toWebWishList.md`. Claude runs `tools/import_wishlist.py` when Sean asks. The script signs in as `import@family-reading.invalid`. Its password is the environment variable `READS_IMPORT_PASSWORD` in the Claude Code environment settings. It is never in this repo. The file in `yc-reading/` has no Reader column; the script takes the reader (YC) from the folder name.

## Firebase settings (Sean, 2026-10-18)

| Setting | Value |
|---|---|
| Project | `family-reading` (ID `family-reading-f4748`) |
| Authentication | Email/Password on. Four accounts as above. Sign-up and delete turned off (User actions). Plus `import@family-reading.invalid` for the import script (Sean, 2026-10-19) |
| Firestore | `(default)` database, `us-west1` |
| API key | "Browser key (auto created by Firebase)". Websites restriction: `https://seanlin-larc.github.io/*`, `http://localhost:8000/*` (set 2026-10-18) |
| Security rules | `firebase/firestore.rules`. Published by Sean in the console (2026-10-19) |

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
