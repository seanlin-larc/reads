"""Browser tests for the Reads sign-in, reader list and tracker pages.

Runs the real pages in headless Chromium. The Firebase SDK files from www.gstatic.com are
replaced by the fake modules in tests/fake/ (no network, no real accounts, test PIN only).
The site is served under /<repo folder>/ to match GitHub Pages (/reads/).

Run from anywhere:  python tests/run.py
Needs:              pip install playwright  (and Chromium for Playwright; see tests/README.md)
Screenshots go to tests/out/ (not committed).
"""
import os, sys, subprocess, time
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
        check("tracker title for JY", pg.text_content("#title") == "JY’s reading", pg.text_content("#title"))
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
        # 11c. no request to Firestore or the Kids Games project
        bad = [r for r in reqs if "firestore" in r or "kidsgame" in r]
        check("no Firestore or Kids Games requests", not bad, bad)

        check("no page errors (online)", not errs, errs)

        # 12. offline: Firebase cannot load
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

        # 13. dark mode screenshot
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
