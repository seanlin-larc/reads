"""Tests for firebase/firestore.rules and tools/import_wishlist.py, with the Firebase emulators.

Run from the repo folder (needs the Firebase CLI and Java 11 or later; see tests/README.md):
  firebase emulators:exec --config firebase/firebase.json --project demo-reads --only auth,firestore "python tests/rules_test.py"

The project ID starts with "demo-", so the emulators never contact the real Firebase project.
The accounts and the password below exist only in the emulator. They are not real.
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))
import import_wishlist as iw

if not iw.emulator():
    sys.exit("Run this with 'firebase emulators:exec' (see the top of this file).")

TEST_PASSWORD = "emulator-only-password"
AUTH = f"http://{os.environ['FIREBASE_AUTH_EMULATOR_HOST']}/identitytoolkit.googleapis.com/v1"
BASE = f"projects/{iw.project()}/databases/(default)/documents"

results = []
def check(name, ok, info=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (("  -- " + str(info)) if not ok and info else ""))

def allowed(fn):
    """True when the request is allowed, False when the rules refuse it."""
    try:
        fn()
        return True
    except RuntimeError as e:
        if "(403)" in str(e):
            return False
        raise

def account(code):
    email = f"{code}@family-reading.invalid"
    iw.call("POST", f"{AUTH}/accounts:signUp?key=demo", {"email": email, "password": TEST_PASSWORD})
    return iw.sign_in(email, TEST_PASSWORD)

def fields(d):
    return {k: iw.to_value(v) for k, v in d.items()}

def get(path, token):
    return lambda: iw.call("GET", iw.docs_url(path), token=token)

def write(path, data, token, mask=None, exists=None, stamp=True):
    w = {"update": {"name": f"{BASE}{path}", "fields": fields(data)}}
    if mask is not None: w["updateMask"] = {"fieldPaths": mask}
    if exists is not None: w["currentDocument"] = {"exists": exists}
    if stamp: w["updateTransforms"] = [{"fieldPath": "updatedAt", "setToServerValue": "REQUEST_TIME"}]
    return lambda: iw.call("POST", iw.docs_url(":commit"), {"writes": [w]}, token=token)

def delete(path, token):
    return lambda: iw.call("POST", iw.docs_url(":commit"), {"writes": [{"delete": f"{BASE}{path}"}]}, token=token)

BOOK = {"title": "Kid Lawyer", "author": "Grisham, John", "series": "Theodore Boone", "seriesNo": 1,
        "status": "Hold", "readOn": None, "finishedOn": None, "addedOn": "2026-10-19", "updatedBy": "import"}

# Start empty, then add two books as the emulator owner (the owner skips the rules).
iw.call("DELETE", f"http://{os.environ['FIRESTORE_EMULATOR_HOST']}/emulator/v1/{BASE}")
write("/readers/YC/books/b1", BOOK, "owner")()
write("/readers/SL/books/s1", dict(BOOK, title="Ghost", series="", seriesNo=None, status="None"), "owner")()

yc, other, imp = account("yc"), account("other"), account("import")

# ---- a reader (YC) ----
check("reader reads own book", allowed(get("/readers/YC/books/b1", yc)))
check("reader reads another reader's book", allowed(get("/readers/SL/books/s1", yc)))
check("reader lists books", allowed(get("/readers/YC/books", yc)))
st = lambda d, mask: write("/readers/YC/books/b1", d, yc, mask=mask, exists=True)
check("reader changes status Hold to EBook", allowed(st({"status": "EBook", "updatedBy": "YC"}, ["status", "updatedBy"])))
check("reader changes status of another reader's book",
      allowed(write("/readers/SL/books/s1", {"status": "Hold", "updatedBy": "YC"}, yc, mask=["status", "updatedBy"], exists=True)))
check("reader sets Reading with readOn", allowed(st({"status": "Reading", "readOn": "2026-10-19"}, ["status", "readOn"])))
check("reader sets Finished with finishedOn", allowed(st({"status": "Finished", "finishedOn": "2026-10-25"}, ["status", "finishedOn"])))
check("reader restores readOn to null (Undo)", allowed(st({"status": "Hold", "readOn": None, "finishedOn": None}, ["status", "readOn", "finishedOn"])))
check("refused: unknown status 'Ready'", not allowed(st({"status": "Ready"}, ["status"])))
check("refused: status 'Ebook' (spelling is EBook)", not allowed(st({"status": "Ebook"}, ["status"])))
check("refused: date not like 2026-10-19", not allowed(st({"readOn": "10/19/2026"}, ["readOn"])))
check("refused: reader changes the title", not allowed(st({"title": "Other"}, ["title"])))
check("refused: reader adds a new field", not allowed(st({"reason": "fun"}, ["reason"])))
check("refused: reader adds a book", not allowed(write("/readers/YC/books/new1", BOOK, yc, exists=False)))
check("refused: reader deletes a book", not allowed(delete("/readers/YC/books/b1", yc)))
check("refused: reader code not in the list", not allowed(get("/readers/XX/books/b1", yc)))
check("refused: other collection", not allowed(get("/notes/n1", yc)))

# ---- not signed in, and an account that is not a reader ----
check("refused: signed out reads", not allowed(get("/readers/YC/books/b1", None)))
check("refused: non-reader account reads", not allowed(get("/readers/YC/books/b1", other)))
check("refused: non-reader account changes status",
      not allowed(write("/readers/YC/books/b1", {"status": "None"}, other, mask=["status"], exists=True)))

# ---- the import account ----
check("import lists books", allowed(get("/readers/YC/books", imp)))
check("import adds a book", allowed(write("/readers/YC/books/i1", dict(BOOK, title="The Accused", seriesNo=3), imp, exists=False)))
check("refused: import adds a book with a bad status", not allowed(write("/readers/YC/books/i2", dict(BOOK, status="Ready"), imp, exists=False)))
check("refused: import adds a 'reason' field", not allowed(write("/readers/YC/books/i3", dict(BOOK, reason="x"), imp, exists=False)))
check("refused: import adds a book with no title", not allowed(write("/readers/YC/books/i4", dict(BOOK, title=""), imp, exists=False)))
check("refused: import changes a book", not allowed(write("/readers/YC/books/b1", {"status": "None"}, imp, mask=["status"], exists=True)))
check("refused: import deletes a book", not allowed(delete("/readers/YC/books/b1", imp)))
check("refused: import writes for code XX", not allowed(write("/readers/XX/books/i5", BOOK, imp, exists=False)))

# ---- the import script, end to end ----
SAMPLE = """# To web wishlist

| Reader | Title | Series | # | Author(s) | Status |
| --- | --- | --- | --- | --- | --- |
| YC | Kid Lawyer | Theodore Boone | 1 | Grisham, John | Hold |
| YC | The Abduction | Theodore Boone | 2 | Grisham, John | ebook |
| YC | The Iron Trial | Magisterium | 1 | Black, Holly; Clare, Cassandra | |
| SL | Holes | — | — | Sachar, Louis | Finished |
"""
def run_import(text, *flags):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
    env = dict(os.environ, READS_IMPORT_PASSWORD=TEST_PASSWORD)
    r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "import_wishlist.py"), f.name, *flags],
                       capture_output=True, text=True, env=env)
    os.unlink(f.name)
    return r.returncode, r.stdout + r.stderr

code, out = run_import(SAMPLE)
n = len(iw.list_books("YC", imp))
check("import dry run writes nothing", code == 0 and "Dry run" in out and n == 2, out)
check("import dry run skips the book already there", "Already there, skip: 1" in out and "New, add: 3" in out, out)
code, out = run_import(SAMPLE, "--write")
yc_books = {b["title"]: b for b in iw.list_books("YC", imp)}
check("import --write adds the new books", code == 0 and "Added 3 books" in out and len(yc_books) == 4, out)
a = yc_books.get("The Abduction", {})
check("imported book has the right fields",
      a.get("status") == "EBook" and a.get("seriesNo") == 2 and a.get("updatedBy") == "import"
      and len(a.get("addedOn") or "") == 10 and "updatedAt" in a, a)
i = yc_books.get("The Iron Trial", {})
check("empty status becomes None; two authors kept", i.get("status") == "None" and i.get("author") == "Black, Holly; Clare, Cassandra", i)
h = [b for b in iw.list_books("SL", imp) if b["title"] == "Holes"]
check("dash cells become empty series and null #", h and h[0]["series"] == "" and h[0]["seriesNo"] is None, h)
code, out = run_import(SAMPLE, "--write")
check("second import adds nothing", code == 0 and "Added 0 books" in out and len(iw.list_books("YC", imp)) == 4, out)
code, out = run_import(SAMPLE.replace("| ebook |", "| Ready |").replace("| SL |", "| XX |"), "--write")
check("bad file: errors listed, nothing written",
      code == 1 and "Ready" in out and "XX" in out and len(iw.list_books("YC", imp)) == 4, out)
NO_READER = "| Title | Series | # | Author(s) |\n|---|---|---|---|\n| Ghost | Track | 1 | Reynolds, Jason |\n"
code, out = run_import(NO_READER, "--write", "--reader", "YC")
check("--reader YC: a file with no Reader column imports to YC",
      code == 0 and "Added 1 books" in out and "Ghost" in {b["title"] for b in iw.list_books("YC", imp)}, out)
env = dict(os.environ); env.pop("READS_IMPORT_PASSWORD", None)
r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "import_wishlist.py"), "/dev/null"], capture_output=True, text=True, env=env)
check("empty file: no books found", r.returncode == 1 and "No books found" in r.stdout, r.stdout)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} passed")
sys.exit(1 if failed else 0)
