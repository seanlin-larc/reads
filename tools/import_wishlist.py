"""Import books from toWebWishList.md (or toWebHistory.md) into Firestore.

Sean writes the books in notes-with-llm/projects/yc-reading/toWebWishList.md. When Sean asks,
Claude runs this script. The script adds each new book to readers/{code}/books in Firestore.
A book that is already there (same reader, title, series and number) is skipped, so the same
file can be imported again.

Usage:
  python tools/import_wishlist.py FILE            dry run: show what the import would add
  python tools/import_wishlist.py FILE --write    add the books
  python tools/import_wishlist.py FILE --check    only read and check the file (no network)
  Add --reader YC when the file has no Reader column. For a file in a folder named
  yc-reading (or sl-, cj-, jy-reading), the reader comes from the folder name (Sean, 2026-10-19).

Sign-in: the import account import@family-reading.invalid. Its password comes from the
environment variable READS_IMPORT_PASSWORD (a secret in the Claude Code environment settings).
The script never prints it. The Firestore rules let this account read books and add books,
but not change or delete them.

Emulator: when FIRESTORE_EMULATOR_HOST and FIREBASE_AUTH_EMULATOR_HOST are set, the script uses
the Firebase emulators, not the real project (see tests/README.md).

File format: a Markdown table. The column names can be in any order; case does not matter.
  | Reader | Title | Series | # | Author(s) | Status |
  | YC | Kid Lawyer | Theodore Boone | 1 | Grisham, John | Hold |
- Reader: SL, CJ, YC or JY. Optional when you give --reader, or when the folder gives it. Title: required.
- Series and #: empty for a book that is not in a series.
- Author(s): "Last, First". More than one author: "Black, Holly; Clare, Cassandra".
- Status: None, Hold, EBook, Reading or Finished. Empty = None.
- Optional columns "Read on" and "Finished on": dates like 2026-10-19.
- Optional column "Log #": the place of a Finished book in an old reading log that has no
  dates (1 = finished first). Reading History uses it for the order. Example: toWebHistory.md.
- A cell with only "—" or "-" is empty.

Standard library only. Python 3.9 or later.
"""
import json, os, re, secrets, string, sys, urllib.error, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT = "family-reading-f4748"
API_KEY = "AIzaSyDmd5-z2gzfaKzdSM1BLuyw2VS0kjDYdAc"   # not a secret; same key as shared/auth.js
REFERER = "https://seanlin-larc.github.io/"            # the API key accepts only this website
IMPORT_EMAIL = "import@family-reading.invalid"
READERS = ["SL", "CJ", "YC", "JY"]
STATUSES = ["None", "Hold", "EBook", "Reading", "Finished"]

# Column name in the file -> field name.
COLUMNS = {
    "reader": "reader", "title": "title", "series": "series",
    "#": "seriesNo", "no": "seriesNo", "no.": "seriesNo", "series #": "seriesNo", "number": "seriesNo",
    "author": "author", "authors": "author", "author(s)": "author",
    "status": "status", "read on": "readOn", "finished on": "finishedOn",
    "log #": "logNo", "log no": "logNo", "log no.": "logNo",
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- read and check the file ----------

def cells(line):
    line = line.strip().replace("\\|", "\0")
    if line.startswith("|"): line = line[1:]
    if line.endswith("|"): line = line[:-1]
    return [c.replace("\0", "|").strip() for c in line.split("|")]

def parse(text, reader=None):
    """Returns (books, errors). Each book is a dict with the Firestore fields plus 'reader'.
    reader: the code to use for rows with no Reader value (from --reader), or None."""
    books, errors, cols = [], [], None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("|"):
            cols = None                       # the table ended
            continue
        row = cells(line)
        if cols is None:                      # header row of a new table
            names = [c.lower() for c in row]
            cols = [COLUMNS.get(c) for c in names] if "title" in names else []
            continue
        if not cols or all(re.fullmatch(r":?-+:?", c) for c in row if c):
            continue                          # not a book table, or the |---| line
        raw = {f: ("" if v in ("—", "-") else v) for f, v in zip(cols, row) if f}
        if not any(raw.values()):
            continue
        if reader and not raw.get("reader"):
            raw["reader"] = reader
        book, problems = check_row(raw)
        if problems:
            errors.append(f"line {n}: " + "; ".join(problems))
        else:
            books.append(book)
    return books, errors

def check_row(raw):
    problems = []
    reader = raw.get("reader", "").upper()
    if not reader:
        problems.append("no reader: add a Reader column, put the file in yc-reading/, or use --reader YC")
    elif reader not in READERS:
        problems.append(f"reader '{raw.get('reader', '')}' is not SL, CJ, YC or JY")
    title = raw.get("title", "")
    if not title:
        problems.append("no title")
    no = raw.get("seriesNo", "")
    if no and not no.isdigit():
        problems.append(f"# '{no}' is not a whole number")
    log = raw.get("logNo", "")
    if log and not log.isdigit():
        problems.append(f"Log # '{log}' is not a whole number")
    status = {s.lower(): s for s in STATUSES}.get(raw.get("status", "").lower() or "none")
    if not status:
        problems.append(f"status '{raw.get('status')}' is not one of {', '.join(STATUSES)}")
    for f in ("readOn", "finishedOn"):
        if raw.get(f) and not DATE.match(raw[f]):
            problems.append(f"date '{raw[f]}' is not like 2026-10-19")
    book = {
        "reader": reader, "title": title, "author": raw.get("author", ""),
        "series": raw.get("series", ""), "seriesNo": int(no) if no.isdigit() else None,
        "status": status, "readOn": raw.get("readOn") or None, "finishedOn": raw.get("finishedOn") or None,
        "logNo": int(log) if log.isdigit() else None,
    }
    return book, problems

def norm(s):
    s = (s or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(s.split())

def key(b):
    return (b["reader"], norm(b["title"]), norm(b["series"]), b["seriesNo"])


# ---------- Firebase (REST) ----------

def emulator():
    return os.environ.get("FIRESTORE_EMULATOR_HOST") and os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")

def project():
    return os.environ.get("GCLOUD_PROJECT", "demo-reads") if emulator() else PROJECT

def call(method, url, body=None, token=None):
    headers = {"Content-Type": "application/json", "Referer": REFERER}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read())["error"]["message"]
        except Exception:
            msg = e.reason
        raise RuntimeError(f"{method} failed ({e.code}): {msg}") from None

def sign_in(email, password):
    """Returns an ID token for the account."""
    if emulator():
        url = f"http://{os.environ['FIREBASE_AUTH_EMULATOR_HOST']}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=demo"
    else:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    return call("POST", url, {"email": email, "password": password, "returnSecureToken": True})["idToken"]

def docs_url(path=""):
    host = f"http://{os.environ['FIRESTORE_EMULATOR_HOST']}" if emulator() else "https://firestore.googleapis.com"
    return f"{host}/v1/projects/{project()}/databases/(default)/documents{path}"

def to_value(v):
    if v is None: return {"nullValue": None}
    if isinstance(v, bool): return {"booleanValue": v}
    if isinstance(v, int): return {"integerValue": str(v)}
    return {"stringValue": str(v)}

def from_value(v):
    if "integerValue" in v: return int(v["integerValue"])
    if "nullValue" in v: return None
    return next(iter(v.values()))

def list_books(reader, token):
    """Returns the books of one reader as a list of dicts (with 'reader' and 'id')."""
    out, page = [], ""
    while True:
        r = call("GET", docs_url(f"/readers/{reader}/books?pageSize=300" + (f"&pageToken={page}" if page else "")), token=token)
        for d in r.get("documents", []):
            b = {k: from_value(v) for k, v in d.get("fields", {}).items()}
            b.update(reader=reader, id=d["name"].rsplit("/", 1)[-1])
            out.append(b)
        page = r.get("nextPageToken")
        if not page:
            return out

def new_id():
    abc = string.ascii_letters + string.digits
    return "".join(secrets.choice(abc) for _ in range(20))

def add_books(books, token, today):
    """Adds the books in batches. Each batch is all or nothing."""
    base = f"projects/{project()}/databases/(default)/documents"
    for i in range(0, len(books), 400):
        writes = []
        for b in books[i:i + 400]:
            fields = {k: to_value(b[k]) for k in ("title", "author", "series", "seriesNo", "status", "readOn", "finishedOn")}
            if b.get("logNo") is not None:
                fields["logNo"] = to_value(b["logNo"])
            fields["addedOn"] = to_value(today)
            fields["updatedBy"] = to_value("import")
            writes.append({
                "update": {"name": f"{base}/readers/{b['reader']}/books/{new_id()}", "fields": fields},
                "currentDocument": {"exists": False},
                "updateTransforms": [{"fieldPath": "updatedAt", "setToServerValue": "REQUEST_TIME"}],
            })
        call("POST", docs_url(":commit"), {"writes": writes}, token=token)


# ---------- main ----------

def reader_from_folder(path):
    """yc-reading/toWebWishList.md -> 'YC'. None when the folder name is not <code>-reading."""
    folder = os.path.basename(os.path.dirname(os.path.abspath(path))).lower()
    code = folder[:-len("-reading")].upper() if folder.endswith("-reading") else ""
    return code if code in READERS else None

def describe(b):
    s = f"{b['reader']}  {b['title']}"
    if b["series"]: s += f"  ({b['series']} #{b['seriesNo']})" if b["seriesNo"] else f"  ({b['series']})"
    return s + f"  [{b['status']}]"

def main(argv):
    args, flags, reader = [], set(), None
    items = iter(argv)
    for a in items:
        if a == "--reader":
            reader = next(items, "").upper()
        elif a.startswith("--reader="):
            reader = a.split("=", 1)[1].upper()
        elif a.startswith("--"):
            flags.add(a)
        else:
            args.append(a)
    if len(args) != 1 or flags - {"--write", "--check"} or (reader is not None and reader not in READERS):
        print(__doc__.split("\n\n")[2])
        return 2
    if reader is None:
        reader = reader_from_folder(args[0])
        if reader:
            print(f"Reader for rows with no Reader value: {reader} (from the folder name).")
    with open(args[0], encoding="utf-8") as f:
        books, errors = parse(f.read(), reader)
    if errors:
        print("The file has problems. Nothing was imported. Fix these lines:")
        for e in errors: print("  " + e)
        return 1
    if not books:
        print("No books found. The file needs a table with a 'Title' column.")
        return 1
    print(f"File: {len(books)} books.")
    if "--check" in flags:
        for b in books: print("  " + describe(b))
        return 0

    password = os.environ.get("READS_IMPORT_PASSWORD")
    if not password:
        print("READS_IMPORT_PASSWORD is not set. Add it as a secret in the Claude Code environment settings.")
        return 1
    token = sign_in(IMPORT_EMAIL, password)

    have = set()
    for r in sorted({b["reader"] for b in books}):
        have |= {key(b) for b in list_books(r, token)}
    add, skip, seen = [], [], set()
    for b in books:
        k = key(b)
        (skip if k in have or k in seen else add).append(b)
        seen.add(k)

    target = "EMULATOR" if emulator() else f"Firestore project {PROJECT}"
    print(f"Target: {target}")
    print(f"Already there, skip: {len(skip)}")
    for b in skip: print("  = " + describe(b))
    print(f"New, add: {len(add)}")
    for b in add: print("  + " + describe(b))
    if "--write" not in flags:
        print("Dry run. Nothing was written. Add --write to add the new books.")
        return 0
    if add:
        add_books(add, token, datetime.now(ZoneInfo("America/Vancouver")).strftime("%Y-%m-%d"))
    print(f"Done. Added {len(add)} books.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
