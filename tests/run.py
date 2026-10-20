"""Browser tests for the Reads sign-in, reader list, wishlist and Reading History pages.

Runs the real pages in headless Chromium. The Firebase SDK files from www.gstatic.com are
replaced by the fake modules in tests/fake/ (no network, no real accounts, test PIN only).
The site is served under /<repo folder>/ to match GitHub Pages (/reads/).

Run from anywhere:  python tests/run.py
Needs:              pip install playwright  (and Chromium for Playwright; see tests/README.md)
Screenshots go to tests/out/ (not committed).
"""
import json, os, sys, subprocess, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.join(HERE, "fake")
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
PORT = 8765
BASE = f"http://localhost:{PORT}/{os.path.basename(REPO)}/"
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--directory", os.path.dirname(REPO)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

results = []
def check(name, ok, info=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (("  -- " + str(info)) if not ok and info else ""))

# 0. The import script reads toWebWishList.md (no network). Firestore writes: tests/rules_test.py.
sys.path.insert(0, os.path.join(REPO, "tools"))
import import_wishlist as iw
books, errors = iw.parse("""Notes above the table are ignored.

| Title | Reader | Author(s) | Series | # | Status |
|:--|---|---|---|---|---|
| Kid Lawyer | yc | Grisham, John | Theodore Boone | 1 | Hold |
| The Iron Trial | YC | Black, Holly; Clare, Cassandra | Magisterium | 1 | |
| Holes | SL | Sachar, Louis | — | — | finished |

| Other table | Title? |
|---|---|
| x | y |
""")
check("import file: 3 books, columns in any order", not errors and [b["title"] for b in books] == ["Kid Lawyer", "The Iron Trial", "Holes"], (books, errors))
check("import file: reader upper case, status names fixed, empty = None",
      [(b["reader"], b["status"]) for b in books] == [("YC", "Hold"), ("YC", "None"), ("SL", "Finished")], books)
check("import file: dash cells are empty", books[2]["series"] == "" and books[2]["seriesNo"] is None and books[0]["seriesNo"] == 1, books)
books, errors = iw.parse("| Reader | Title | # | Status |\n|---|---|---|---|\n| ZZ | A | 1 | Hold |\n| YC | | 2 | Hold |\n| YC | B | two | Ready |\n| YC | C | 3 | Ebook |\n")
check("import file: bad rows reported with line numbers",
      len(errors) == 3 and "line 3" in errors[0] and "ZZ" in errors[0] and "no title" in errors[1] and "two" in errors[2] and "Ready" in errors[2], errors)
check("import file: status spelling EBook", [b["status"] for b in books] == ["EBook"], books)
books, errors = iw.parse("| Title | Reader | Status |\n|---|---|---|\n| A | | Hold |\n| B | SL | |\n", "YC")
check("import file: --reader fills rows with no reader; a Reader value wins",
      not errors and [(b["title"], b["reader"]) for b in books] == [("A", "YC"), ("B", "SL")], (books, errors))
books, errors = iw.parse("| Title |\n|---|\n| A |\n")
check("import file: no reader and no --reader is an error", len(errors) == 1 and "--reader YC" in errors[0], errors)
books, errors = iw.parse("| Log # | Title | Status | Finished on |\n|---|---|---|---|\n| 1 | A | Finished | |\n| 2 | B | Finished | 2026-10-13 |\n| x | C | Finished | |\n", "YC")
check("import file: Log # column read as logNo; bad Log # reported",
      [(b["title"], b["logNo"], b["finishedOn"]) for b in books] == [("A", 1, None), ("B", 2, "2026-10-13")]
      and len(errors) == 1 and "Log # 'x'" in errors[0], (books, errors))
books, errors = iw.parse("| Title |\n|---|\n| A |\n", "YC")
check("import file: no Log # column gives logNo None", books[0]["logNo"] is None, books)
SCRIPT = os.path.join(REPO, "tools", "import_wishlist.py")
with open(os.path.join(OUT, "no-reader.md"), "w", encoding="utf-8") as f:
    f.write("| Title | Series | # | Author(s) | Status |\n|---|---|---|---|---|\n| Kid Lawyer | Theodore Boone | 1 | Grisham, John | Hold |\n")
r = subprocess.run([sys.executable, SCRIPT, os.path.join(OUT, "no-reader.md"), "--check", "--reader", "yc"], capture_output=True, text=True)
check("import --check --reader yc: file OK", r.returncode == 0 and "YC  Kid Lawyer" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, SCRIPT, os.path.join(OUT, "no-reader.md"), "--check", "--reader=XX"], capture_output=True, text=True)
check("import --reader XX is refused", r.returncode == 2, r.stdout + r.stderr)
os.makedirs(os.path.join(OUT, "yc-reading"), exist_ok=True)
with open(os.path.join(OUT, "yc-reading", "toWebWishList.md"), "w", encoding="utf-8") as f:
    f.write("| Title | Status |\n|---|---|\n| Ghost | Hold |\n")
r = subprocess.run([sys.executable, SCRIPT, os.path.join(OUT, "yc-reading", "toWebWishList.md"), "--check"], capture_output=True, text=True)
check("import: a file in yc-reading/ gets reader YC", r.returncode == 0 and "YC  Ghost" in r.stdout and "from the folder name" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, SCRIPT, os.path.join(OUT, "yc-reading", "toWebWishList.md"), "--check", "--reader", "SL"], capture_output=True, text=True)
check("import: --reader wins over the folder name", r.returncode == 0 and "SL  Ghost" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, SCRIPT, os.path.join(OUT, "no-reader.md"), "--check"], capture_output=True, text=True)
check("import: other folder and no --reader is an error", r.returncode == 1 and "no reader" in r.stdout, r.stdout + r.stderr)

def fake_route(route):
    name = route.request.url.rsplit("/", 1)[-1]
    with open(os.path.join(FAKE, name)) as f:
        route.fulfill(status=200, content_type="application/javascript", body=f.read())

def new_page(ctx):
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    return pg, errs

def type_pin(pg, pin):
    for d in pin:
        pg.click(f'#pad button[data-key="{d}"]')

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.route("https://www.gstatic.com/firebasejs/13.0.0/*", fake_route)
        pg, errs = new_page(ctx)
        reqs = []
        pg.on("request", lambda r: reqs.append(r.url))

        # 1. fresh visit
        pg.goto(BASE)
        pg.wait_for_selector("#signin:not([hidden])")
        codes = pg.eval_on_selector_all("#players button", "els => els.map(e => e.textContent)")
        check("sign-in shows SL CJ YC JY only", codes == ["SL", "CJ", "YC", "JY"], codes)
        check("no-internet note hidden online", pg.is_hidden("#noNet"))
        pg.screenshot(path=os.path.join(OUT, "1-signin.png"))

        # 2. PIN before picking a person
        pg.click('#pad button[data-key="1"]')
        check("PIN without person asks to pick", "Pick your name first" in pg.text_content("#msg"))

        # 3. wrong PIN
        pg.click('#players button[data-code="YC"]')
        type_pin(pg, "111111")
        pg.wait_for_function("document.querySelector('#msg').textContent.includes('Wrong PIN')")
        check("wrong PIN counted", "9 tries left" in pg.text_content("#msg"), pg.text_content("#msg"))

        # 4. correct PIN by keyboard -> readers
        for d in "135790":
            pg.keyboard.press(d)
        pg.wait_for_url(BASE + "readers/")
        pg.wait_for_selector("#content:not([hidden])")
        check("bar shows Signed in as YC", "Signed in as YC" in pg.text_content("#who"), pg.text_content("#who"))
        cards = pg.eval_on_selector_all(".readers a", "els => els.map(e => [e.querySelector('.code').textContent, e.getAttribute('href'), !!e.querySelector('.you')])")
        check("four reader cards with links", [c[:2] for c in cards] == [["SL", "../tracker/?reader=SL"], ["CJ", "../tracker/?reader=CJ"], ["YC", "../tracker/?reader=YC"], ["JY", "../tracker/?reader=JY"]], cards)
        check("only YC card marked You", [c[2] for c in cards] == [False, False, True, False], cards)
        lock = pg.evaluate("localStorage.getItem('rd-lock')")
        check("YC email used", pg.evaluate("JSON.parse(localStorage.getItem('fake-auth-user')).email") == "yc@family-reading.invalid")
        check("correct PIN clears wrong-PIN count", lock in (None, "{}"), lock)
        pg.screenshot(path=os.path.join(OUT, "2-readers.png"), full_page=True)

        # 5. sign-in page while signed in -> readers
        pg.goto(BASE)
        pg.wait_for_url(BASE + "readers/")
        check("sign-in page skips to readers when signed in", True)

        # 6. open a tracker
        pg.wait_for_selector("#content:not([hidden])")
        pg.click('.readers a[href="../tracker/?reader=JY"]')
        pg.wait_for_selector("#content:not([hidden])")
        check("tracker title for JY", pg.text_content("#title") == "JY’s Wish List", pg.text_content("#title"))
        check("tracker bar shows YC", "Signed in as YC" in pg.text_content("#who"))
        pg.screenshot(path=os.path.join(OUT, "3-tracker.png"))

        # 7. bad reader -> readers
        pg.goto(BASE + "tracker/?reader=Guest")
        pg.wait_for_url(BASE + "readers/")
        check("unknown reader goes back to readers", True)

        # 8. sign out
        pg.wait_for_selector("#content:not([hidden])")
        pg.click("#who button")
        pg.wait_for_url(BASE)
        pg.wait_for_selector("#signin:not([hidden])")
        check("sign-out returns to sign-in", pg.evaluate("localStorage.getItem('fake-auth-user')") is None)
        check("last person preselected", pg.get_attribute('#players button[data-code="YC"]', "aria-checked") == "true")

        # 9. guarded pages while signed out
        pg.goto(BASE + "readers/")
        pg.wait_for_url(BASE)
        check("readers page needs sign-in", True)
        pg.goto(BASE + "tracker/?reader=YC")
        pg.wait_for_url(BASE)
        check("tracker page needs sign-in", True)

        # 10. lock after 10 wrong PINs; no Firebase call while locked
        pg.wait_for_selector("#signin:not([hidden])")
        pg.click('#players button[data-code="CJ"]')
        for i in range(10):
            type_pin(pg, "000000")
            pg.wait_for_function("!document.querySelector('#pad button').disabled")
        check("10 wrong PINs lock CJ", "CJ is locked for 30 more minutes" in pg.text_content("#msg"), pg.text_content("#msg"))
        calls = pg.evaluate("localStorage.getItem('fake-calls')")
        type_pin(pg, "135790")
        check("locked person: PIN not sent", pg.evaluate("localStorage.getItem('fake-calls')") == calls)
        pg.click('#players button[data-code="SL"]')
        check("other person not locked", "Hi SL" in pg.text_content("#msg"), pg.text_content("#msg"))
        pg.reload()
        pg.wait_for_selector("#signin:not([hidden])")
        pg.click('#players button[data-code="CJ"]')
        check("lock survives reload", "locked" in pg.text_content("#msg"))
        pg.evaluate("""(() => { const a = JSON.parse(localStorage.getItem('rd-lock')); a.CJ.until = Date.now() - 1; a.CJ.at = Date.now() - 1800001; localStorage.setItem('rd-lock', JSON.stringify(a)); })()""")
        pg.click('#players button[data-code="SL"]'); pg.click('#players button[data-code="CJ"]')
        check("lock ends after 30 minutes", "Hi CJ" in pg.text_content("#msg"), pg.text_content("#msg"))
        check("Kids Games lock key untouched", pg.evaluate("localStorage.getItem('kg-lock')") is None)

        # 11. an account that is not one of the four people is refused and signed out
        pg.evaluate("localStorage.setItem('fake-auth-user', JSON.stringify({uid:'uid-other', email:'other@family-reading.invalid'}))")
        pg.goto(BASE + "readers/")
        pg.wait_for_url(BASE)
        pg.wait_for_selector("#signin:not([hidden])")
        check("non-reader session refused and signed out", pg.evaluate("localStorage.getItem('fake-auth-user')") is None)
        # 11b. emails use @family-reading.invalid
        pg.click('#players button[data-code="CJ"]')
        type_pin(pg, "135790")
        pg.wait_for_url(BASE + "readers/")
        pg.wait_for_selector("#content:not([hidden])")
        u = pg.evaluate("JSON.parse(localStorage.getItem('fake-auth-user'))")
        check("CJ signs in with cj@family-reading.invalid", u and u["email"] == "cj@family-reading.invalid", u)
        check("bar shows Signed in as CJ", "Signed in as CJ" in pg.text_content("#who"))
        pg.click("#who button")
        pg.wait_for_url(BASE)
        pg.wait_for_selector("#signin:not([hidden])")
        # 11c. no request to the real Firestore or the Kids Games project (the fake SDK files are allowed)
        bad = [r for r in reqs if "firestore.googleapis" in r or "kidsgame" in r]
        check("no Firestore or Kids Games requests", not bad, bad)

        check("no page errors (online)", not errs, errs)

        # 12. wishlist and Reading History with fake Firestore books (signed in as SL)
        tc = b.new_context(viewport={"width": 390, "height": 844})
        tc.route("https://www.gstatic.com/firebasejs/13.0.0/*", fake_route)
        pt, terrs = new_page(tc)
        pt.goto(BASE + "shared/style.css")
        bk = lambda t, a, st, series="", no=None, **k: dict(title=t, author=a, status=st, series=series, seriesNo=no, **k)
        db = {"readers/YC/books": {
            "a": bk("Kid Lawyer", "Grisham, John", "Reading", "Theodore Boone", 1, readOn="2026-10-02"),
            "b": bk("The Abduction", "Grisham, John", "EBook", "Theodore Boone", 2),
            "c": bk("The Activist", "Grisham, John", "None", "Theodore Boone", 4),
            "d": bk("Angel", "Patterson, James", "Hold", "Maximum Ride", 7),
            "e": bk("The Westing Game", "Raskin, Ellen", "Hold"),
            "f": bk("Ghost", "Reynolds, Jason", "None", "Track", 1),
            "g": bk("Holes", "Sachar, Louis", "Finished"),
            "h": bk("Wrath of the Triple Goddess", "Riordan, Rick", "Finished", "Percy Jackson", 7, readOn="2026-09-25", finishedOn="2026-10-15"),
            "i": bk("Masterminds", "Korman, Gordon", "Finished", logNo=1),
            "j": bk("Star-Crossed", "Dee, Barbara", "Finished", logNo=81),
            "k": bk("Spy School", "Gibbs, Stuart", "Finished", logNo=3),
        }, "readers/SL/books": {"s": bk("Other list", "X", "None")}}
        pt.evaluate("db => { localStorage.setItem('fake-db', JSON.stringify(db)); localStorage.setItem('fake-auth-user', JSON.stringify({uid:'uid-sl', email:'sl@family-reading.invalid'})); }", db)
        pt.goto(BASE + "tracker/?reader=YC")
        pt.wait_for_selector("#books .book")
        titles = lambda: pt.eval_on_selector_all("#books .book .t", "els => els.map(e => e.textContent)")
        status_of = lambda t: pt.evaluate("t => [...document.querySelectorAll('#books .book')].find(li => li.querySelector('.t').textContent === t)?.querySelector('.status').textContent", t)
        tap_status = lambda t: pt.locator("#books .book", has_text=t).locator(".status").click()
        writes = lambda: pt.evaluate("JSON.parse(localStorage.getItem('fake-writes') || '[]')")
        today = pt.evaluate("new Date().toLocaleDateString('en-CA')")
        check("wishlist title for YC", pt.text_content("#title") == "YC’s Wish List" and pt.title() == "YC’s Wish List · Reads", [pt.text_content("#title"), pt.title()])
        check("wishlist order: Hold, EBook, None, Reading at the bottom",
              titles() == ["Angel", "The Westing Game", "The Abduction", "The Activist", "Ghost", "Kid Lawyer"], titles())
        check("wishlist hides Finished books; count", pt.text_content("#count") == "6 books", pt.text_content("#count"))
        rows = pt.eval_on_selector_all("#books .book", "els => els.map(e => [...e.querySelectorAll('.t,.m')].map(x => x.textContent))")
        check("row shows title, series and #, author", rows[0] == ["Angel", "Maximum Ride · #7", "Patterson, James"], rows[0])
        check("row with no series shows title and author only", rows[1] == ["The Westing Game", "Raskin, Ellen"], rows[1])
        check("Reading History link", pt.get_attribute("#historyLink", "href") == "../history/?reader=YC")
        pt.click("#export")
        opts = pt.eval_on_selector_all("#exportCard .flip button", "els => els.map(e => e.dataset.format)")
        check("Export opens a card with Markdown and JSON", pt.is_visible("#exportCard") and opts == ["Markdown", "JSON"]
              and pt.text_content("#exportTitle") == "Export YC’s Wish List", (opts, pt.text_content("#exportCard")))
        small = pt.evaluate("[...document.querySelectorAll('#exportCard button')].map(e => e.getBoundingClientRect()).filter(r => r.height < 44).length")
        check("Export card: tap targets at least 44 px, no horizontal scroll", small == 0 and pt.evaluate("document.documentElement.scrollWidth") <= 390, small)
        pt.screenshot(path=os.path.join(OUT, "6b-export-card.png"))
        pt.click("#exportCard .close")
        check("Export card: Close closes it and saves nothing", pt.locator("#exportCard").count() == 0 and pt.locator(".shade:visible").count() == 0)
        pt.click("#export")
        pt.keyboard.press("Escape")
        check("Export card: Escape closes it", pt.locator("#exportCard").count() == 0)
        pt.click("#export")
        with pt.expect_download() as dl:
            pt.click("#exportCard button[data-format=Markdown]")
        with open(dl.value.path(), encoding="utf-8") as f:
            text = f.read()
        got, errors = iw.parse(text, "YC")
        check("Export card closes after a choice", pt.locator("#exportCard").count() == 0)
        check("wishlist Export: file name with reader and date", dl.value.suggested_filename == f"YC-wish-list-{today}.md", dl.value.suggested_filename)
        check("wishlist Export: heading, then the books in the page order",
              text.startswith("# YC’s Wish List\n") and not errors and [x["title"] for x in got] == titles(), (text, errors))
        check("wishlist Export: import script reads status, series, author, Read on",
              [(x["status"], x["series"], x["seriesNo"], x["author"], x["readOn"]) for x in got][-1] == ("Reading", "Theodore Boone", 1, "Grisham, John", "2026-10-02")
              and got[1]["series"] == "" and got[1]["seriesNo"] is None, got)
        pt.click("#export")
        with pt.expect_download() as dl:
            pt.click("#exportCard button[data-format=JSON]")
        with open(dl.value.path(), encoding="utf-8") as f:
            data = json.load(f)
        check("wishlist JSON: file name with reader and date", dl.value.suggested_filename == f"YC-wish-list-{today}.json", dl.value.suggested_filename)
        check("wishlist JSON: title, date, count, books in the page order",
              data["title"] == "YC’s Wish List" and data["exported"] == today and data["count"] == 6
              and [x["title"] for x in data["books"]] == titles(), data)
        check("wishlist JSON: fields of each book, empty is null",
              data["books"][-1] == {"title": "Kid Lawyer", "series": "Theodore Boone", "seriesNo": 1, "author": "Grisham, John", "status": "Reading", "readOn": "2026-10-02"}
              and data["books"][1]["series"] is None and data["books"][1]["seriesNo"] is None, data["books"])
        md = pt.evaluate("""async () => (await import('../shared/books.js')).toMarkdown('T', [{title: 'A | B', author: 'X,\\nY', series: '', seriesNo: null, status: 'None'}], ['Title', 'Series', '#', 'Author(s)', 'Status'])""")
        got, errors = iw.parse(md, "YC")
        check("Export: a | in a cell and a line break are kept safe", not errors and got[0]["title"] == "A | B" and got[0]["author"] == "X, Y", (md, got, errors))
        pt.screenshot(path=os.path.join(OUT, "6-wishlist.png"), full_page=True)

        tap_status("Angel")
        opts = pt.eval_on_selector_all("#sheet .flip button", "els => els.map(e => [e.firstChild.textContent.trim(), e.getAttribute('aria-pressed')])")
        check("status button opens the flipper with 5 statuses",
              pt.is_visible("#sheet") and opts == [["None", "false"], ["Hold", "true"], ["EBook", "false"], ["Reading", "false"], ["Finished", "false"]], opts)
        pt.screenshot(path=os.path.join(OUT, "7-flipper.png"))
        small = pt.evaluate("""[...document.querySelectorAll('.status, .navbtn, #sheet button, #who button')]
            .filter(e => e.offsetParent).map(e => e.getBoundingClientRect()).filter(r => r.height < 44).length""")
        check("tap targets at least 44 px", small == 0, small)
        pt.click("#sheet .flip button:has-text('EBook')")
        w = writes()[-1]
        check("EBook: no confirm, saved at once", pt.is_hidden("#sheet") and w["path"] == "readers/YC/books/d"
              and w["fields"]["status"] == "EBook" and w["fields"]["updatedBy"] == "SL" and w["fields"]["updatedAt"] == {"fakeServerTime": True}, w)
        check("list follows the change", status_of("Angel") == "EBook" and titles()[1] == "Angel", titles())
        check("Undo bar shows", pt.is_visible("#undo") and pt.text_content("#undoText") == "EBook: Angel", pt.text_content("#undoText"))
        pt.click("#undoBtn")
        check("Undo restores the status", status_of("Angel") == "Hold" and writes()[-1]["fields"] == {"status": "Hold", "readOn": None, "finishedOn": None, "updatedAt": {"fakeServerTime": True}, "updatedBy": "SL"}, writes()[-1])
        n = len(writes())
        tap_status("Angel")
        pt.click("#sheet .flip button:has-text('Reading')")
        check("Reading asks to confirm", pt.text_content("#sheet .ask") == "Checked out?" and len(writes()) == n, pt.text_content("#sheet"))
        pt.screenshot(path=os.path.join(OUT, "8-confirm.png"))
        pt.click("#sheet .two button:has-text('Cancel')")
        check("Cancel goes back to the flipper, no change", pt.is_visible("#sheet .flip") and len(writes()) == n and status_of("Angel") == "Hold")
        pt.click("#sheet .flip button:has-text('Reading')")
        pt.click("#sheet .two .yes")
        w = writes()[-1]
        check("Yes, Reading: status and readOn today", w["fields"]["status"] == "Reading" and w["fields"]["readOn"] == today and status_of("Angel") == "Reading", w)
        tap_status("Kid Lawyer")
        pt.click("#sheet .flip button:has-text('Finished')")
        check("Finished asks to confirm", "moves to Reading History" in pt.text_content("#sheet .ask"))
        pt.click("#sheet .two .yes")
        w = writes()[-1]
        check("Yes, Finished: finishedOn today, book leaves the wishlist",
              w["path"] == "readers/YC/books/a" and w["fields"]["status"] == "Finished" and w["fields"]["finishedOn"] == today and "Kid Lawyer" not in titles(), w)
        check("Undo bar names Reading History", pt.text_content("#undoText") == "Moved to Reading History: Kid Lawyer")
        tap_status("Ghost")
        pt.keyboard.press("Escape")
        check("Escape closes the flipper", pt.is_hidden("#sheet"))
        check("writes only to YC's books", all(x["path"].startswith("readers/YC/books/") for x in writes()))
        check("no horizontal scroll at 390 px", pt.evaluate("document.documentElement.scrollWidth") <= 390)

        pt.click("#historyLink")
        pt.wait_for_url(BASE + "history/?reader=YC")
        pt.wait_for_selector("#books .book")
        hist = pt.eval_on_selector_all("#books .book", "els => els.map(e => [...e.querySelectorAll('.t,.m')].map(x => x.textContent))")
        check("Reading History title", pt.text_content("#title") == "YC’s Reading History", pt.text_content("#title"))
        check("Reading History: dated books newest first, then old log by Log # (newest first), then no date",
              [h[0] for h in hist] == ["Kid Lawyer", "Wrath of the Triple Goddess", "Star-Crossed", "Spy School", "Masterminds", "Holes"], hist)
        check("Reading History count", pt.text_content("#count") == "6 books finished", pt.text_content("#count"))
        check("Reading History shows read and finished dates",
              hist[0][-1] == f"Read 2026-10-02 → finished {today}" and hist[1][-1] == "Read 2026-09-25 → finished 2026-10-15" and hist[2] == ["Star-Crossed", "Dee, Barbara"] and hist[5] == ["Holes", "Sachar, Louis"], hist)
        check("Reading History has no status buttons", pt.locator("#books .status").count() == 0)
        check("Reading History back link", pt.get_attribute("#back", "href") == "../tracker/?reader=YC" and pt.text_content("#back") == "← YC’s Wish List", pt.text_content("#back"))
        pt.click("#export")
        check("Reading History Export opens the card", pt.text_content("#exportTitle") == "Export YC’s Reading History"
              and pt.eval_on_selector_all("#exportCard .flip button", "els => els.map(e => e.dataset.format)") == ["Markdown", "JSON"])
        with pt.expect_download() as dl:
            pt.click("#exportCard button[data-format=Markdown]")
        with open(dl.value.path(), encoding="utf-8") as f:
            text = f.read()
        got, errors = iw.parse(text, "YC")
        check("Reading History Export: file name with reader and date", dl.value.suggested_filename == f"YC-reading-history-{today}.md", dl.value.suggested_filename)
        check("Reading History Export: heading, books in the page order, Log # and dates",
              text.startswith("# YC’s Reading History\n") and not errors
              and [(x["title"], x["status"], x["logNo"], x["finishedOn"]) for x in got] == [
                  ("Kid Lawyer", "Finished", None, today), ("Wrath of the Triple Goddess", "Finished", None, "2026-10-15"),
                  ("Star-Crossed", "Finished", 81, None), ("Spy School", "Finished", 3, None), ("Masterminds", "Finished", 1, None), ("Holes", "Finished", None, None)],
              (text, got, errors))
        pt.click("#export")
        with pt.expect_download() as dl:
            pt.click("#exportCard button[data-format=JSON]")
        with open(dl.value.path(), encoding="utf-8") as f:
            data = json.load(f)
        check("Reading History JSON: file name, Log # and dates",
              dl.value.suggested_filename == f"YC-reading-history-{today}.json" and data["count"] == 6
              and [(x["title"], x["logNo"], x["finishedOn"]) for x in data["books"]] == [
                  ("Kid Lawyer", None, today), ("Wrath of the Triple Goddess", None, "2026-10-15"),
                  ("Star-Crossed", 81, None), ("Spy School", 3, None), ("Masterminds", 1, None), ("Holes", None, None)],
              (dl.value.suggested_filename, data))
        check("Export button: 44 px tall, no horizontal scroll", pt.evaluate("document.getElementById('export').getBoundingClientRect().height") >= 44
              and pt.evaluate("document.documentElement.scrollWidth") <= 390)
        pt.screenshot(path=os.path.join(OUT, "9-history.png"), full_page=True)
        pt.goto(BASE + "tracker/?reader=JY")
        pt.wait_for_selector("#books .empty")
        check("empty wishlist message", pt.text_content("#books .empty") == "No books on the Wish List.")
        pt.goto(BASE + "history/?reader=Guest")
        pt.wait_for_url(BASE + "readers/")
        check("history: unknown reader goes back to readers", True)
        pt.evaluate("localStorage.setItem('fake-db-error', 'permission-denied')")
        pt.goto(BASE + "tracker/?reader=YC")
        pt.wait_for_selector("#problem:not([hidden])")
        check("Firestore refusal shows a message", "rules may not be published" in pt.text_content("#problem"), pt.text_content("#problem"))
        pt.evaluate("localStorage.removeItem('fake-db-error'); localStorage.removeItem('fake-auth-user')")
        pt.goto(BASE + "history/?reader=YC")
        pt.wait_for_url(BASE)
        check("history page needs sign-in", True)
        check("no page errors (wishlist and history)", not terrs, terrs)

        # 12b. dark mode screenshots
        dkt = b.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
        dkt.route("https://www.gstatic.com/firebasejs/13.0.0/*", fake_route)
        pdt, _ = new_page(dkt)
        pdt.goto(BASE + "shared/style.css")
        pdt.evaluate("db => { localStorage.setItem('fake-db', JSON.stringify(db)); localStorage.setItem('fake-auth-user', JSON.stringify({uid:'uid-yc', email:'yc@family-reading.invalid'})); }", db)
        pdt.goto(BASE + "tracker/?reader=YC")
        pdt.wait_for_selector("#books .book")
        pdt.screenshot(path=os.path.join(OUT, "10-wishlist-dark.png"), full_page=True)
        pdt.locator("#books .book", has_text="Angel").locator(".status").click()
        pdt.screenshot(path=os.path.join(OUT, "11-flipper-dark.png"))
        pdt.keyboard.press("Escape")
        pdt.click("#export")
        pdt.screenshot(path=os.path.join(OUT, "11b-export-card-dark.png"))
        pdt.goto(BASE + "history/?reader=YC")
        pdt.wait_for_selector("#books .book")
        pdt.screenshot(path=os.path.join(OUT, "12-history-dark.png"), full_page=True)

        # 13. offline: Firebase cannot load
        off = b.new_context(viewport={"width": 390, "height": 844})
        off.route("https://www.gstatic.com/firebasejs/13.0.0/*", lambda r: r.abort())
        po, perrs = new_page(off)
        po.goto(BASE)
        po.wait_for_selector("#signin:not([hidden])", timeout=20000)
        check("offline: sign-in shows no-internet note", po.is_visible("#noNet"))
        po.click('#players button[data-code="YC"]')
        type_pin(po, "135790")
        po.wait_for_function("document.querySelector('#msg').classList.contains('bad')", timeout=20000)
        check("offline: PIN attempt not counted as wrong", "No internet" in po.text_content("#msg"), po.text_content("#msg"))
        po.goto(BASE + "readers/")
        po.wait_for_selector("#problem:not([hidden])", timeout=20000)
        check("offline: readers page shows message", "No internet" in po.text_content("#problem"))

        # 14. dark mode screenshot
        dk = b.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
        dk.route("https://www.gstatic.com/firebasejs/13.0.0/*", fake_route)
        pd, _ = new_page(dk)
        pd.goto(BASE)
        pd.wait_for_selector("#signin:not([hidden])")
        pd.click('#players button[data-code="SL"]')
        pd.screenshot(path=os.path.join(OUT, "4-signin-dark.png"))
        type_pin(pd, "135790")
        pd.wait_for_url(BASE + "readers/")
        pd.wait_for_selector("#content:not([hidden])")
        pd.screenshot(path=os.path.join(OUT, "5-readers-dark.png"))
        b.close()
finally:
    srv.terminate()

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} passed")
sys.exit(1 if failed else 0)
