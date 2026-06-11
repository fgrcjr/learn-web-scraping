# 🕷️ Learn Web Scraping — Practice Playground

A single-page sandbox for practicing web scraping. Every common scraping scenario
is laid out as its own section, organized into **five complexity levels** — the more
layers of nesting and the more moving parts, the higher the level.

Every example has a collapsible **"View HTML source"** block underneath it showing
the markup *as initially served* (captured before any JavaScript runs) — so you can
study the structure you're targeting without opening DevTools. For Level 5 sections
the source block is intentionally empty or minimal: that's the point — the data
isn't in the initial HTML.

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
| **5** | Dynamic (JavaScript required) | JS-injected content, delayed loading, click-to-reveal, "load more" button, infinite scroll, JS tabs, JSON embedded in `<script>` tags, Shadow DOM, honeypot bot traps, randomized IDs |

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
