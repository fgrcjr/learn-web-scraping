# 🕷️ Learn Web Scraping — Practice Playground

A single-page sandbox for practicing web scraping. Every common scraping scenario
is laid out as its own section, organized into **five complexity levels** — the more
layers of nesting and the more moving parts, the higher the level.

Every example has two collapsible code panels underneath it:

- **"View HTML source"** — the markup *as initially served* (captured before any
  JavaScript runs). For Level 5 sections this is intentionally empty or minimal:
  that's the point — the data isn't in the initial HTML.
- **"View live DOM"** — re-renders in real time as you interact with the example
  (click a tab and watch the `active` class move; click "load more" and watch items
  append), flashing on every change. The diff between the two panels is exactly
  what JavaScript did — the core distinction between scraping with an HTTP parser
  versus a headless browser.

## Getting started

Open `index.html` directly in a browser, or serve it locally (recommended, so the
iframe and dynamic sections work consistently):

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

Point your scraper at it:

```python
# Static parsing (Levels 1–4)
import requests
from bs4 import BeautifulSoup

soup = BeautifulSoup(requests.get("http://localhost:8000").text, "html.parser")
print(soup.select_one("#unique-paragraph").text)

# Dynamic content (Level 5)
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto("http://localhost:8000")
    page.wait_for_selector("#js-rendered li")
    print(page.locator("#js-rendered li").all_text_contents())
```

## Complexity levels

| Level | Theme | Scenarios |
|-------|-------|-----------|
| **1** | Flat elements (no nesting) | Headings & text, every link flavor (absolute/relative/anchor/mailto/tel/query-params/nofollow), images (src/srcset/lazy `data-src`/base64), `data-*` attributes, meta tags |
| **2** | Simple containers (one layer) | Unordered/ordered/definition lists, simple table, full form (all input types, hidden CSRF token, select/multi-select/textarea), media (video/audio/figure/progress/meter), semantic tags |
| **3** | Nested structures (2–3 layers) | Multi-level nested lists, complex tables (thead/tbody/tfoot, colspan/rowspan, nested table), product card grid with missing fields, dropdown nav menus, breadcrumbs & pagination (`rel="next"`), accordions & fieldsets |
| **4** | Deep & tricky (4+ layers) | Recursive comment threads, schema.org microdata + JSON-LD, messy legacy markup, obfuscated class names (`data-testid` anchoring), 5 kinds of hidden elements, iframes (`src` and `srcdoc`), article extraction with interleaved ads/junk |
| **5** | Dynamic (JavaScript required) | JS-injected content, delayed loading, click-to-reveal, "load more" button, infinite scroll, JS tabs, JSON embedded in `<script>` tags, Shadow DOM, honeypot bot traps, randomized IDs, cookie-consent overlay, AJAX from a JSON endpoint, client-side sortable table |

Levels 3–4 also cover: search forms with GET parameters, relative dates & international
number/date formats, obfuscated emails (entities, CSS-reversed, JS-assembled), and data
encoded only in class names (the books.toscrape star-rating gotcha).

## Mini-sites (multi-page crawling practice)

The `mini-sites/` folder contains small multi-page sites that replicate the structure of
famous practice sandboxes, so you can practice *crawling* (following links), not just parsing:

- `mini-sites/quotes/` — quote cards with microdata, tags, and "Next" pagination (modeled on [quotes.toscrape.com](https://quotes.toscrape.com))
- `mini-sites/books/` — 2-page catalogue + product detail pages; ratings encoded in class names, truncated titles, product-info tables (modeled on [books.toscrape.com](https://books.toscrape.com))
- `mini-sites/countries/` — label/value country data (modeled on [scrapethissite.com](https://www.scrapethissite.com/pages/simple/))

`data/products.json` serves as a fake AJAX endpoint for scenario 5.12.

## Training & evaluating a scraper (ground truth)

If you're building a general-purpose scraper, this repo doubles as a labeled test set.
There are **28 extraction tasks** with expected output, in two tiers:

- **15 static tasks** (`ground-truth/manifest.json`) — solvable with an HTTP request and
  an HTML/XML parser. Sources include the friendly pages above, a hostile corpus, and
  hashed framework identifiers (CSS Modules, styled-components, Vue scoped attributes,
  utility-class soup) where hash-dependent selectors are a wrong answer.
- **13 browser tasks** (`ground-truth/browser-manifest.json`) — the Level 5 dynamic
  scenarios, where the data does not exist in the served HTML: JS-injected content,
  delayed loading, click-to-reveal (random value, matched by regex), load-more,
  infinite scroll, tabs, JSON-in-script, shadow DOM, honeypot detection, randomized
  IDs, cookie-banner dismissal, AJAX, and a sortable table (order-sensitive scoring).

The hostile corpus for the static tier:

- `corpus/malformed.html` — unclosed/mis-nested tags, unquoted attributes
- `corpus/legacy-layout.html` — 1998-style nested-table layout, `<font>` tags everywhere
- `corpus/no-semantics.html` — no ids, no classes, no semantic tags
- `corpus/intl.html` — German/Japanese/French/Arabic (RTL) content needing normalization
- `corpus/feed.xml` — RSS (XML, not HTML)

Workflow:

```bash
# 1. See what each task expects (sources, schema, answer file)
cat ground-truth/manifest.json

# 2. Run your scraper against the source pages; write one JSON per task:
#    out/quotes.json, out/books.json, out/corpus-malformed.json, ...

# 3. Score it (order-insensitive lists, float tolerance, diff per failure)
python3 evaluate.py out
```

The answer key is `solutions/reference_scraper.py` (BeautifulSoup), which regenerates
all 14 answers and scores 14/14:

```bash
pip install beautifulsoup4
python3 solutions/reference_scraper.py            # 15 static answers

pip install playwright && python3 -m playwright install chromium
python3 solutions/reference_browser_scraper.py    # 13 browser answers (serves HTTP itself)

python3 evaluate.py solutions/output              # 28/28
```

## Graduate to real sites

These live sites exist specifically for legal scraping practice (also linked at the bottom
of the playground page): [books.toscrape.com](https://books.toscrape.com),
[quotes.toscrape.com](https://quotes.toscrape.com) (with `/js`, `/scroll`, `/login` variants),
[scrapethissite.com](https://www.scrapethissite.com/pages/),
[webscraper.io/test-sites](https://webscraper.io/test-sites),
[the-internet.herokuapp.com](https://the-internet.herokuapp.com),
[httpbin.org](https://httpbin.org), the [Open Library API](https://openlibrary.org/developers/api),
and (politely) [Wikipedia](https://en.wikipedia.org).

## Suggested exercises

1. **Level 1–2:** Extract all links with their `href` and text into a CSV. Parse the simple table into a list of dicts.
2. **Level 3:** Scrape the product grid into JSON — handle the card with no rating and the one with a sale price (`<del>`/`<ins>`).
3. **Level 3:** Flatten the complex table correctly despite `colspan`/`rowspan`.
4. **Level 4:** Write a recursive parser for the comment thread that records each comment's depth.
5. **Level 4:** Find all 5 hidden secrets in section 4.5 from the raw HTML.
6. **Level 5:** Get all 15 "load more" articles by clicking the button with Playwright.
7. **Level 5:** Extract the user records from the `#initial-state` JSON script **without** a browser — just `requests` + `json`.
8. **Level 5:** Detect the honeypot field in the contact form programmatically (hint: computed visibility).

## Files

- `index.html` — the playground (all levels, self-contained CSS/JS)
- `iframe-content.html` — separate document loaded by the iframe scenario (4.6)

Scrape responsibly: respect `robots.txt`, rate limits, and terms of service. 🕸️
