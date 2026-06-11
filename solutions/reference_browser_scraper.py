#!/usr/bin/env python3
"""Reference scraper for the DYNAMIC (Level 5) tasks in
ground-truth/browser-manifest.json.

Unlike reference_scraper.py, these tasks cannot be solved by parsing the
served HTML: the data is created by JavaScript, so we drive a real headless
browser with Playwright — waiting, clicking, and scrolling like a user.

This is the answer key — try each task yourself before reading it.

Usage:
    pip install playwright && python3 -m playwright install chromium
    python3 solutions/reference_browser_scraper.py    # writes solutions/output/*.json
    python3 evaluate.py solutions/output              # scores static + browser tasks

The script serves the repo over local HTTP itself (the AJAX task needs it).
"""
import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "output"


# ----------------------------------------------------------------- tasks
# Each task receives a live page with index.html loaded.

def cookie_banner(page):
    banner_appeared = page.locator("#cookie-banner").count() == 1
    page.click("#cookie-accept")
    return {
        "banner_appeared": banner_appeared,
        "consent_after_accept": page.locator("#cookie-status").get_attribute("data-consent"),
        "banner_present_after": page.locator("#cookie-banner").count() > 0,
    }


def js_rendered(page):
    page.wait_for_selector("#js-rendered li.planet")
    return page.locator("#js-rendered li.planet").all_text_contents()


def delayed_content(page):
    # explicit wait for the element — never a blind sleep
    el = page.wait_for_selector("#late-arrival", timeout=5000)
    return {
        "answer": int(el.query_selector("strong").inner_text()),
        "data_loaded": el.get_attribute("data-loaded") == "true",
    }


def click_reveal(page):
    page.click("#reveal-btn")
    return {"code": page.locator("#secret-code strong").inner_text()}


def load_more(page):
    while page.locator("#load-more-btn").count():
        page.click("#load-more-btn")
    items = page.locator("#load-more-list li").all_text_contents()
    return {
        "count": len(items),
        "first": items[0],
        "last": items[-1],
        "button_gone": page.locator("#load-more-btn").count() == 0,
    }


def infinite_scroll(page):
    box = page.locator("#infinite-box")
    prev = -1
    while True:
        count = page.locator("#infinite-box .scroll-item").count()
        if count == prev:
            break  # no growth since last scroll: we've hit the end
        prev = count
        box.evaluate("el => el.scrollTop = el.scrollHeight")
        page.wait_for_timeout(150)
    items = page.locator("#infinite-box .scroll-item").all_text_contents()
    return {"count": len(items), "last": items[-1]}


def tabs(page):
    result = {}
    for btn in page.locator("#tab-widget .tab-buttons button").all():
        name = btn.get_attribute("data-tab")
        btn.click()
        result[name] = page.locator("#tab-widget .tab-panel.active").inner_text().strip()
    return result


def embedded_json(page):
    # the goldmine: the full dataset is sitting in a script tag
    state = json.loads(page.locator("script#initial-state").text_content())
    return {
        "total_users": state["totalUsers"],
        "users": [{"name": u["name"], "role": u["role"]} for u in state["users"]],
    }


def shadow_dom(page):
    # Playwright selectors pierce open shadow roots automatically
    return {"text": page.locator("#shadow-host .shadow-secret").inner_text()}


def honeypot(page):
    fields = page.eval_on_selector_all(
        "#contact-form input[type=text]",
        "els => els.map(el => ({name: el.name, visible: el.offsetParent !== null}))")
    return {
        "visible_fields": [f["name"] for f in fields if f["visible"]],
        "honeypot_fields": [f["name"] for f in fields if not f["visible"]],
    }


def stable_fields(page):
    return page.eval_on_selector_all(
        "#random-id-zone span[data-field]",
        "els => Object.fromEntries(els.map(el => [el.dataset.field, el.textContent]))")


def ajax_products(page):
    page.click("#ajax-load-btn")
    page.wait_for_selector("li.ajax-product")
    items = page.eval_on_selector_all(
        "li.ajax-product",
        "els => els.map(el => ({id: +el.dataset.productId, text: el.textContent}))")
    rows = []
    for item in items:
        text = item["text"]
        rows.append({
            "id": item["id"],
            "name": text.split(" — $")[0],
            "price": float(re.search(r"\$([\d.]+)", text).group(1)),
            "in_stock": "out of stock" not in text,
        })
    return rows


def sortable_table(page):
    def names():
        return page.locator("#sortable-table tbody tr td:first-child").all_text_contents()
    page.click('#sortable-table th[data-sort="score"]')
    asc = names()
    page.click('#sortable-table th[data-sort="score"]')
    return {"names_by_score_asc": asc, "names_by_score_desc": names()}


TASKS = {
    # the cookie banner overlays the page, so dismiss it first —
    # exactly what a real scraper has to do
    "cookie-banner": cookie_banner,
    "js-rendered": js_rendered,
    "delayed-content": delayed_content,
    "click-reveal": click_reveal,
    "load-more": load_more,
    "infinite-scroll": infinite_scroll,
    "tabs": tabs,
    "embedded-json": embedded_json,
    "shadow-dom": shadow_dom,
    "honeypot": honeypot,
    "stable-fields": stable_fields,
    "ajax-products": ajax_products,
    "sortable-table": sortable_table,
}


def main():
    OUT.mkdir(exist_ok=True)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"http://127.0.0.1:{port}/index.html")
        for name, fn in TASKS.items():
            result = fn(page)
            size = len(result) if isinstance(result, (list, dict)) else 1
            (OUT / f"{name}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {name}: {size} records/fields")
        browser.close()
    server.shutdown()
    print(f"\nWrote {len(TASKS)} files to {OUT}")


if __name__ == "__main__":
    main()
