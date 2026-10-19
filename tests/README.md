# Tests

Browser tests for the sign-in page, the reader list and the tracker placeholder. They run the real pages in headless Chromium. The Firebase SDK files are replaced by small fake modules in `fake/`, so the tests need no network, no real account and no real PIN.

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

Last result (Claude, 2026-10-19): 31 of 31 passed.

## What the fake Firebase does

- `fake/firebase-app.js`: keeps the config. `getAuth` refuses a config that is not `family-reading-f4748`.
- `fake/firebase-auth.js`: accounts `sl@`, `cj@`, `yc@`, `jy@family-reading.invalid`, plus `other@family-reading.invalid` (a non-reader, to test refusal). One fake test PIN for all. The signed-in user is kept in `localStorage` key `fake-auth-user`.

## What is covered

Sign-in with the four people, wrong PIN, the 10-PIN lock (and that a locked PIN is not sent), sign-out, last person preselected, guarded pages, the reader list and links, the tracker title and unknown `reader` values, refusal of a non-reader account, no requests to Firestore or the Kids Games project, and no-internet messages.

## Not covered

- Real Firebase sign-in. Test on the live site with a real PIN.
- Firestore rules. When rules exist, test them with the Firestore emulator (`firebase emulators:exec`; needs Java 11 or later).

## When you change the pages

Add or change checks in `run.py` in the same commit. Keep the fake modules in step with the functions that `shared/auth.js` imports from the Firebase SDK.
