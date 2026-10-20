# Tests

Browser tests for the sign-in page, the reader list, the wishlist and Reading History. A second test checks the Firestore rules and the import script with the Firebase emulators. They run the real pages in headless Chromium. The Firebase SDK files are replaced by small fake modules in `fake/`, so the tests need no network, no real account and no real PIN.

## Run

```
pip install playwright
python -m playwright install chromium   # skip if Chromium for Playwright is already installed
python tests/run.py
```

- Cloud session: Chromium is already in `/opt/pw-browsers`. Do not run `playwright install`. Install the Playwright version that matches that Chromium build. On 2026-10-19 the build was `chromium-1194`, so `pip install playwright==1.56.0`. With a newer Playwright, the launch fails with "Executable doesn't exist".
- The script serves the repo folder at `http://localhost:8765/<repo folder>/`, the same path shape as GitHub Pages (`/reads/`).
- It prints `PASS` or `FAIL` for each check, then a total. The exit code is 1 if a check fails.
- Screenshots (phone size, light and dark) go to `tests/out/`. That folder is not committed.

Last result (Claude, 2026-10-20): 94 of 94 passed.

## What the fake Firebase does

- `fake/firebase-app.js`: keeps the config. `getAuth` refuses a config that is not `family-reading-f4748`.
- `fake/firebase-firestore.js`: books in `localStorage` key `fake-db` (`{"readers/YC/books": {id: book}}`). Each `updateDoc` is added to `fake-writes`. Set `fake-db-error` (for example `permission-denied`) to make the book list fail.
- `fake/firebase-auth.js`: accounts `sl@`, `cj@`, `yc@`, `jy@family-reading.invalid`, plus `other@family-reading.invalid` (a non-reader, to test refusal). One fake test PIN for all. The signed-in user is kept in `localStorage` key `fake-auth-user`.

## What is covered

- `run.py`: sign-in with the four people, wrong PIN, the 10-PIN lock (and that a locked PIN is not sent), sign-out, last person preselected, guarded pages, the reader list and links, unknown `reader` values, refusal of a non-reader account, no requests to the real Firestore or the Kids Games project, and no-internet messages.
- `run.py`, wishlist and Reading History: list order (Reading History: date, then `logNo` of the old reading log), what each row shows, the status flipper, confirmation for Reading and Finished, Cancel, Undo, dates set to today, Finished books moving to Reading History, tap targets of 44 px, empty list, Firestore refusal message. Export on both pages: the card with Markdown and JSON, Close and Escape, tap targets; for each format the file name, book order and fields; and that `tools/import_wishlist.py` reads the Markdown file back.
- `run.py`, import file: reading the `toWebWishList.md` table and the error messages (no network).
- `rules_test.py`: what each account can read, change, add and delete; and the import script end to end (dry run, write, second import adds nothing, bad file).

## Firestore rules test (emulator)

Needs Java 11 or later and the Firebase CLI (`npm install -g firebase-tools`). From the repo folder:

```
firebase emulators:exec --config firebase/firebase.json --project demo-reads --only auth,firestore "python tests/rules_test.py"
```

- The project ID starts with `demo-`, so the emulators never contact the real Firebase project. The test accounts and password exist only in the emulator.
- The first run downloads the emulators (about 60 MB) from Google.

Last result (Claude, 2026-10-20): 42 of 42 passed. Also checked once by hand (not in the repo): the real Firebase SDK 13.0.0 in Chromium against the emulator, with the same calls as `shared/auth.js` (offline copy, live list, status change, Undo, a refused change).

## Not covered

- Real Firebase sign-in and the real Firestore. Test on the live site with a real PIN.
- The offline copy on a real iPhone (no signal in the library).

## When you change the pages

Add or change checks in `run.py` in the same commit. Keep the fake modules in step with the functions that `shared/auth.js` imports from the Firebase SDK. When you change `firebase/firestore.rules` or `tools/import_wishlist.py`, run `rules_test.py` too.
