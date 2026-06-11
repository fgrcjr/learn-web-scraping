#!/usr/bin/env python3
"""Reference scraper: produces the ground-truth answers for every task in
ground-truth/manifest.json by actually scraping the pages in this repo.

This is the answer key — try each task yourself before reading it.

Usage:
    pip install beautifulsoup4
    python3 solutions/reference_scraper.py            # writes solutions/output/*.json
    python3 evaluate.py solutions/output              # should score 14/14
"""
import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "output"


def soup_of(relpath: str, parser: str = "html.parser") -> BeautifulSoup:
    return BeautifulSoup((ROOT / relpath).read_text(encoding="utf-8"), parser)


def money(text: str) -> float:
    """Parse a comma-thousands money string like '$13,500' or '£51.77'.

    Extracts the first numeric token rather than stripping characters: symbols
    like the dirham's 'د.إ' contain dots, so naive stripping corrupts the number.
    """
    return float(re.search(r"\d[\d,]*(?:\.\d+)?", text).group().replace(",", ""))


# ---------------------------------------------------------------- index.html

def data_attributes():
    soup = soup_of("index.html")
    rows = []
    for el in soup.select("#s1-attributes [data-product-id]"):
        rows.append({
            "sku": el["data-product-id"],
            "name": el.get_text(strip=True),
            "price": float(el["data-price"]),
            "currency": el["data-currency"],
            "in_stock": el["data-in-stock"] == "true",
        })
    return rows


def simple_table():
    soup = soup_of("index.html")
    rows = []
    for tr in soup.select("#simple-table tr")[1:]:  # first row is headers
        country, capital, pop = [td.get_text(strip=True) for td in tr.select("td")]
        rows.append({"country": country, "capital": capital, "population_m": float(pop)})
    return rows


def product_cards():
    soup = soup_of("index.html")
    rows = []
    for card in soup.select("#products .product-card"):
        price_el = card.select_one(".price")
        sale = price_el.select_one("ins")
        rating_el = card.select_one(".rating")
        reviews_el = card.select_one(".review-count")
        rows.append({
            "sku": card["data-sku"],
            "name": card.select_one(".name").get_text(strip=True),
            "category": card["data-category"],
            "price": float(sale["data-value"] if sale else price_el["data-value"]),
            "original_price": float(price_el.select_one("del")["data-value"]) if sale else None,
            "rating": float(rating_el["data-stars"]) if rating_el else None,
            "review_count": int(re.sub(r"[^\d]", "", reviews_el.get_text())) if reviews_el else None,
            "in_stock": "out-of-stock" not in card.get("class", []),
        })
    return rows


def comment_thread():
    soup = soup_of("index.html")
    rows = []

    def walk(container, depth):
        # only direct-child comments; replies are handled by recursion
        for comment in container.find_all("div", class_="comment", recursive=False):
            meta = comment.find("p", class_="meta").get_text()
            rows.append({
                "id": comment["data-comment-id"],
                "author": comment.find("p", class_="author").get_text(strip=True),
                "depth": depth,
                "upvotes": int(re.search(r"(\d+) upvotes", meta).group(1)),
                "body": comment.find("p", class_="body").get_text(strip=True),
            })
            replies = comment.find("div", class_="replies", recursive=False)
            if replies:
                walk(replies, depth + 1)

    walk(soup.select_one("#comment-thread"), 0)
    return rows


def hidden_secrets():
    soup = soup_of("index.html")
    # hidden ≠ absent: every secret is right there in the HTML
    return [p.get_text(strip=True)
            for p in soup.select('#s4-hidden .sandbox p[id^="hidden-"]')]


# ---------------------------------------------------------------- mini-sites

def quotes():
    """A real micro-crawl: start at page 1 and follow the Next link."""
    rows, page = [], "mini-sites/quotes/index.html"
    while page:
        soup = soup_of(page)
        for q in soup.select(".quote"):
            rows.append({
                "text": q.select_one(".text").get_text(strip=True),
                "author": q.select_one(".author").get_text(strip=True),
                "tags": [t.get_text(strip=True) for t in q.select("a.tag")],
            })
        nxt = soup.select_one(".pager .next a")
        page = f"mini-sites/quotes/{nxt['href']}" if nxt else None
    return rows


RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def books():
    rows = []
    for page in ("mini-sites/books/index.html", "mini-sites/books/page2.html"):
        soup = soup_of(page)
        for pod in soup.select("article.product_pod"):
            rating_classes = pod.select_one(".star-rating")["class"]
            rows.append({
                # the truncated link text lies; the full title is in the attribute
                "title": pod.select_one("h3 a")["title"],
                "price_gbp": money(pod.select_one(".price_color").get_text()),
                "rating": next(RATING_WORDS[c] for c in rating_classes if c in RATING_WORDS),
                "in_stock": "instock" in pod.select_one(".availability")["class"],
            })
    return rows


def book_details():
    rows = []
    for page in ("mini-sites/books/the-art-of-parsing_1.html",
                 "mini-sites/books/headless-and-heartless_2.html"):
        soup = soup_of(page)
        info = {tr.th.get_text(strip=True): tr.td.get_text(strip=True)
                for tr in soup.select("table tr")}
        rows.append({
            "title": soup.select_one("h1").get_text(strip=True),
            "upc": info["UPC"],
            "available": int(re.search(r"\((\d+) available\)", info["Availability"]).group(1)),
            "tax_gbp": money(info["Tax"]),
        })
    return rows


def countries():
    soup = soup_of("mini-sites/countries/index.html")
    rows = []
    for c in soup.select(".country"):
        raw_name = c.select_one(".country-name").get_text(strip=True)
        rows.append({
            "name": re.sub(r"^[^\w]+", "", raw_name),  # strip the flag emoji
            "capital": c.select_one(".country-capital").get_text(strip=True),
            "population": int(c.select_one(".country-population").get_text(strip=True)),
            "area_km2": float(c.select_one(".country-area").get_text(strip=True)),
        })
    return rows


def hashed_classes():
    """Four framework hashing patterns, four strategies — and not one selector
    that would break when the hashes change on the next deploy."""
    soup = soup_of("index.html")
    rows = []

    # A. CSS Modules: the prefix is semantic and stable; match it, not the hash
    for card in soup.select('#hashed-cssmodules [class*="TalkCard_card__"]'):
        rows.append({
            "framework": "css-modules",
            "title": card.select_one('[class*="TalkCard_title__"]').get_text(strip=True),
            "speaker": card.select_one('[class*="TalkCard_speaker__"]').get_text(strip=True),
            "time": card.select_one('[class*="TalkCard_time__"]').get_text(strip=True),
        })

    # B. styled-components: classes are noise — anchor on structure + label text
    for card in soup.select("#hashed-styled > div"):
        labels = {p.b.get_text(strip=True).rstrip(":"): p.b.next_sibling.strip()
                  for p in card.find_all("p") if p.b}
        rows.append({
            "framework": "styled-components",
            "title": card.h5.get_text(strip=True),
            "speaker": labels["Speaker"],
            "time": labels["Time"],
        })

    # C. Vue scoped: the data-v-* attribute is the hash — simply ignore it
    for card in soup.select("#hashed-vue .talk"):
        rows.append({
            "framework": "vue-scoped",
            "title": card.select_one(".title").get_text(strip=True),
            "speaker": card.select_one(".speaker").get_text(strip=True),
            "time": card.select_one(".time").get_text(strip=True),
        })

    # D. utility soup: semantic tags + content patterns, no classes at all
    for card in soup.select("#hashed-utility article"):
        spans = [s.get_text(strip=True) for s in card.find_all("span")]
        rows.append({
            "framework": "utility",
            "title": card.h5.get_text(strip=True),
            "speaker": next(s[3:] for s in spans if s.startswith("by ")),
            "time": next(s for s in spans if re.fullmatch(r"\d{2}:\d{2}", s)),
        })

    return rows


# -------------------------------------------------------------------- corpus

def corpus_malformed():
    # html.parser recovers from the unclosed/mis-nested tags
    soup = soup_of("corpus/malformed.html")
    rows = []
    for li in soup.select("#cars li"):
        rows.append({
            "id": li["data-id"],
            "title": li.b.get_text(strip=True),
            "price": money(li.select_one(".price").get_text()),
            "mileage_km": int(re.search(r"([\d,]+) km", li.get_text()).group(1).replace(",", "")),
        })
    return rows


def corpus_legacy():
    soup = soup_of("corpus/legacy-layout.html")
    # the data table is the one with a bordercolor, nested inside layout tables
    table = soup.find("table", attrs={"bordercolor": True})
    rows = []
    for tr in table.find_all("tr")[1:]:
        name, dept, ext = [td.get_text(strip=True) for td in tr.find_all("td")]
        rows.append({"name": name, "department": dept, "extension": ext})
    return rows


def corpus_no_semantics():
    soup = soup_of("corpus/no-semantics.html")
    rows = []
    for card in soup.select("body > div > div"):
        lines = card.find_all("div", recursive=False)
        company, location = [s.get_text(strip=True) for s in lines[1].find_all("span")]
        salary = lines[2].find_all("span")[1].get_text()
        lo, hi = re.findall(r"₱([\d,]+)", salary)
        rows.append({
            "title": lines[0].get_text(strip=True),
            "company": company,
            "location": location,
            "salary_min": int(lo.replace(",", "")),
            "salary_max": int(hi.replace(",", "")),
            "posted": lines[3].find_all("span")[1].get_text(strip=True),
        })
    return rows


MONTHS = {
    # German                  # French            # Arabic
    "Januar": 1, "Februar": 2, "janvier": 1, "février": 2, "يناير": 1, "فبراير": 2,
    "März": 3, "April": 4, "mars": 3, "avril": 4, "مارس": 3, "أبريل": 4,
    "Mai": 5, "Juni": 6, "mai": 5, "juin": 6, "مايو": 5, "يونيو": 6,
    "Juli": 7, "August": 8, "juillet": 7, "août": 8, "يوليو": 7, "أغسطس": 8,
    "September": 9, "Oktober": 10, "septembre": 9, "octobre": 10, "سبتمبر": 9, "أكتوبر": 10,
    "November": 11, "Dezember": 12, "novembre": 11, "décembre": 12, "نوفمبر": 11, "ديسمبر": 12,
}


def corpus_intl():
    soup = soup_of("corpus/intl.html")
    rows = []
    for listing in soup.select(".listing"):
        lang = listing["lang"]
        price_text = listing.select_one(".price").get_text(strip=True)
        date_text = listing.select_one(".date").get_text(strip=True)

        if lang in ("de", "fr"):  # 1.299,00 € / 1 234,56 € — comma is the decimal
            value = float(re.sub(r"[^\d,]", "", price_text).replace(",", "."))
            currency = "EUR"
        elif lang == "ja":        # ¥12,800
            value, currency = money(price_text), "JPY"
        else:                     # ar: 500.00 د.إ (UAE dirham)
            value, currency = money(price_text), "AED"

        if lang == "ja":  # 2026年6月10日
            y, m, d = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_text).groups()
            iso = f"{y}-{int(m):02d}-{int(d):02d}"
        else:  # "11. Juni 2026" / "9 juin 2026" / "8 يونيو 2026"
            day, month_word, year = re.search(
                r"(\d{1,2})\.?\s+([^\s\d،]+)\s+(\d{4})", date_text).groups()
            iso = f"{year}-{MONTHS[month_word]:02d}-{int(day):02d}"

        rows.append({
            "title": listing.select_one(".title").get_text(strip=True),
            "price_value": value,
            "currency": currency,
            "date": iso,
            "location": listing.select_one(".location").get_text(strip=True),
        })
    return rows


def feed():
    tree = ET.parse(ROOT / "corpus/feed.xml")
    rows = []
    for item in tree.findall(".//item"):
        rows.append({
            "title": item.findtext("title"),
            "link": item.findtext("link"),
            "pub_date": parsedate_to_datetime(item.findtext("pubDate")).isoformat(),
        })
    return rows


TASKS = {
    "data-attributes": data_attributes,
    "simple-table": simple_table,
    "product-cards": product_cards,
    "comment-thread": comment_thread,
    "hidden-secrets": hidden_secrets,
    "hashed-classes": hashed_classes,
    "quotes": quotes,
    "books": books,
    "book-details": book_details,
    "countries": countries,
    "corpus-malformed": corpus_malformed,
    "corpus-legacy": corpus_legacy,
    "corpus-no-semantics": corpus_no_semantics,
    "corpus-intl": corpus_intl,
    "feed": feed,
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, fn in TASKS.items():
        result = fn()
        (OUT / f"{name}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {name}: {len(result)} records")
    print(f"\nWrote {len(TASKS)} files to {OUT}")


if __name__ == "__main__":
    main()
