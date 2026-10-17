# Reads

Family reading trackers: wishlists, library holds and checkouts, for each family member. Static web pages on GitHub Pages, with Firebase for sign-in and (later) the data.

- Site (after GitHub Pages is turned on): https://seanlin-larc.github.io/reads/
- Notes and decisions: `projects/reading-tracker/` in the private `notes-with-llm` repo.

## Status (2026-10-16)

| Part | Status |
|---|---|
| Sign-in page (`index.html`) | Built |
| Reader list, the table of contents (`readers/`) | Built |
| One reader's tracker (`tracker/?reader=YC`) | Placeholder only. Not built |
| Firestore rules for tracker data | Not written |
| GitHub Pages | Not turned on |

## Folder structure

```
reads/
├── index.html          Sign-in: pick a person, type the PIN
├── readers/index.html  Table of contents: pick whose tracker to open
├── tracker/index.html  One person's tracker (placeholder), for example tracker/?reader=YC
├── shared/
│   ├── auth.js         Firebase: sign-in, sign-out, player lookup
│   ├── load.js         Loads auth.js with a time limit, page guard, signed-in bar (no Firebase)
│   ├── lock.js         Wrong-PIN lock on this device (no Firebase)
│   └── style.css       Shared styles, light and dark
├── .nojekyll           Tells GitHub Pages not to run Jekyll
└── README.md
```

## Sign-in

- The site uses the Firebase project of Kids Games (`kidsgame-7a262`) and the same accounts: `sl@`, `cj@`, `yc@`, `jy@kidsgames.invalid`. The 6-digit PIN is the password. Firebase checks the PIN on its server. No PIN or PIN hash is in this public code.
- Guest is not a player here.
- The player code comes from the Firestore document `players/{uid}`, the same as in Kids Games. The current Kids Games rules already allow a signed-in family account to read it.
- **One sign-in for both sites.** Both sites are on the origin `https://seanlin-larc.github.io` and use the same Firebase app config. So a person who signs in on Kids Games is also signed in here, and the reverse. Sign-out on one site also signs out on the other.
- **Wrong-PIN lock:** 10 wrong PINs in a row lock that person for 30 minutes, on this device only (`localStorage` key `rd-lock`). This is a check in the page, not a server check. It is separate from the Kids Games lock (`kg-lock`).
- The API key is not a secret. Its Websites restriction (`https://seanlin-larc.github.io/*`, `http://localhost:8000/*`) already covers this site.

## Device storage keys

All keys start with `rd-`: `rd-lock` (wrong-PIN counter), `rd-lastPlayer` (last person picked on this device).

## Local test

Run `python -m http.server 8000` in this folder, then open `http://localhost:8000/`. Opening the files from disk does not work.

## Rules for changes

- Use relative links only (`href="readers/"`), never `href="/readers/"`. The site is under `/reads/`.
- Keep the Firebase SDK version the same as Kids Games (13.0.0).
- Put the LLM name first in each commit message, for example `Claude: add tracker page`.
