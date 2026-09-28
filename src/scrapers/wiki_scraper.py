"""Scrape Fandom Dark Souls wikis through the MediaWiki API.

Resumable: pages already saved in data/raw/wiki/<wiki>/ are skipped.
Usage:  python -m src.scrapers.wiki_scraper --wiki all [--limit 50]
"""
import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

from src.config import RAW_DIR, REQUEST_DELAY, WIKIS
from src.scrapers.http import get_json, make_session

log = logging.getLogger("wiki")

JUNK_SELECTORS = [
    "script", "style", "table.navbox", ".navbox", "#toc", ".toc", ".mw-editsection",
    "sup.reference", ".noprint", ".wikia-gallery", ".gallery", ".reference", "figure",
    ".mbox", ".hatnote", "aside.portable-infobox .pi-image",
]


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _infobox_lines(aside) -> list[str]:
    lines = []
    for item in aside.select(".pi-data"):
        label, value = item.select_one(".pi-data-label"), item.select_one(".pi-data-value")
        if label and value:
            lines.append(f"{_text(label)}: {_text(value)}")
    return lines


def html_to_sections(html: str) -> list[dict]:
    """Turn parsed wiki HTML into [{'heading': str, 'text': str}, ...]."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.mw-parser-output") or soup

    # Pull infoboxes out first (they hold stats/lore facts) before deleting junk.
    infobox_lines = []
    for aside in root.select("aside.portable-infobox"):
        infobox_lines += _infobox_lines(aside)
        aside.decompose()
    for sel in JUNK_SELECTORS:
        for el in root.select(sel):
            el.decompose()

    sections = [{"heading": "Summary", "lines": []}]
    if infobox_lines:
        sections.append({"heading": "Infobox", "lines": infobox_lines})
        sections.append({"heading": "Summary", "lines": []})

    for el in root.find_all(["h2", "h3", "h4", "p", "ul", "ol", "table", "dl"], recursive=True):
        if el.name in ("h2", "h3", "h4"):
            sections.append({"heading": _text(el), "lines": []})
        elif el.name == "p":
            t = _text(el)
            if t:
                sections[-1]["lines"].append(t)
        elif el.name in ("ul", "ol"):
            if el.find_parent(["ul", "ol", "table"]):  # avoid double-counting nested lists
                continue
            for li in el.find_all("li", recursive=False):
                t = _text(li)
                if t:
                    sections[-1]["lines"].append("- " + t)
        elif el.name == "dl":
            t = _text(el)
            if t:
                sections[-1]["lines"].append(t)
        elif el.name == "table":
            for tr in el.find_all("tr"):
                cells = [_text(c) for c in tr.find_all(["th", "td"])]
                if any(cells):
                    sections[-1]["lines"].append(" | ".join(cells))

    out = []
    for s in sections:
        text = "\n".join(s["lines"]).strip()
        if text:
            out.append({"heading": s["heading"], "text": text})
    return out


def list_titles(session, base: str):
    params = {"action": "query", "list": "allpages", "aplimit": 500, "apnamespace": 0,
              "apfilterredir": "nonredirects", "format": "json"}
    while True:
        data = get_json(session, f"{base}/api.php", params)
        for p in data["query"]["allpages"]:
            yield p["title"]
        if "continue" not in data:
            return
        params.update(data["continue"])
        time.sleep(REQUEST_DELAY)


def fetch_page(session, base: str, title: str) -> dict | None:
    data = get_json(session, f"{base}/api.php", {
        "action": "parse", "page": title, "prop": "text|categories", "redirects": 1,
        "format": "json", "formatversion": 2, "disablelimitreport": 1,
    })
    if "parse" not in data:
        return None
    p = data["parse"]
    return {"title": p["title"], "html": p["text"],
            "categories": [c["category"].replace("_", " ") for c in p.get("categories", [])]}


def out_path(wiki_key: str, title: str) -> Path:
    slug = re.sub(r"[^\w\-]+", "_", title)[:100]
    h = hashlib.sha1(title.encode()).hexdigest()[:8]
    return RAW_DIR / "wiki" / wiki_key / f"{slug}__{h}.json"


def scrape_wiki(key: str, limit: int | None, delay: float):
    cfg, session = WIKIS[key], make_session()
    (RAW_DIR / "wiki" / key).mkdir(parents=True, exist_ok=True)
    log.info("[%s] listing pages from %s", key, cfg["base"])
    titles = list(list_titles(session, cfg["base"]))
    if limit:
        titles = titles[:limit]
    log.info("[%s] %d pages to consider", key, len(titles))

    saved = skipped = failed = 0
    for title in tqdm(titles, desc=key, mininterval=30):
        path = out_path(key, title)
        if path.exists():
            skipped += 1
            continue
        try:
            page = fetch_page(session, cfg["base"], title)
            if not page:
                failed += 1
                continue
            sections = html_to_sections(page["html"])
            if not sections:
                continue
            doc = {
                "source": "fandom", "wiki": key, "game": cfg["game"], "title": page["title"],
                "url": f"{cfg['base']}/wiki/{page['title'].replace(' ', '_')}",
                "categories": page["categories"], "sections": sections,
                "text": "\n\n".join(f"## {s['heading']}\n{s['text']}" for s in sections),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
            saved += 1
        except Exception as e:  # keep the long job alive
            failed += 1
            log.error("[%s] failed on %r: %s", key, title, e)
        time.sleep(delay)
    log.info("[%s] done: saved=%d skipped=%d failed=%d", key, saved, skipped, failed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="all", choices=["all", *WIKIS])
    ap.add_argument("--limit", type=int, default=None, help="max pages per wiki (for testing)")
    ap.add_argument("--delay", type=float, default=REQUEST_DELAY)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for key in (WIKIS if args.wiki == "all" else [args.wiki]):
        scrape_wiki(key, args.limit, args.delay)


if __name__ == "__main__":
    main()
