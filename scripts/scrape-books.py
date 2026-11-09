#!/usr/bin/env python3
"""Книги Чехова в «Читай-городе» → data/books-source.json.

Отличие от общего сборщика: карточки выдачи не содержат автора в подписи
(«Вишневый сад» без «(Антон Чехов)»), поэтому фильтр по подписи даёт ноль книг.
Автора берём из JSON-LD карточки товара, а кандидатов — со страницы автора
и из нескольких поисковых запросов.

Запуск: python scripts/scrape-books.py [--limit N]
"""
import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}
BASE = "https://www.chitai-gorod.ru"
AUTHOR_SURNAME = "маяковск"
# Товары магазина, которые не являются книгой автора: стикеры, обложки, наклейки и т. п.
MERCH = ("стикер", "обложка для книг", "наклейка", "постер", "плакат", "ежедневник",
         "блокнот", "шопер", "значок", "пазл", "кружка", "открытк", "закладк", "карта ")


def fetch(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last = e
            wait = int(e.headers.get("Retry-After") or 0) or (4 * (attempt + 1))
            time.sleep(min(wait, 40) if e.code == 429 else 2)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{type(last).__name__}: {last}")


def product_links(page_html):
    out = {}
    for m in re.finditer(r'<a[^>]+href="(/product/[^"]+)"', page_html):
        href = m.group(1).split("?")[0]
        pid = re.search(r"-(\d+)$", href)
        if pid:
            out.setdefault(pid.group(1), href)
    return out


def book_meta(page_html):
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page_html, re.S):
        try:
            data = json.loads(block)
        except Exception:  # noqa: BLE001
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") not in ("Book", "Product"):
                continue
            authors = node.get("author")
            authors = authors if isinstance(authors, list) else ([authors] if authors else [])
            names = [a.get("name") if isinstance(a, dict) else str(a) for a in authors]
            img = node.get("image")
            if isinstance(img, list):
                img = img[0] if img else None
            if isinstance(img, dict):
                img = img.get("url") or img.get("contentUrl")
            offer = node.get("offers") if isinstance(node.get("offers"), dict) else {}
            avail = offer.get("availability") or ""
            return {
                "title": html.unescape(node.get("name") or ""),
                "authors": [html.unescape(n) for n in names if n],
                "isbn": node.get("isbn") or "",
                "pages": node.get("numberOfPages") or "",
                "publisher": html.unescape(node.get("publisher") or "") if isinstance(node.get("publisher"), str) else "",
                "image": img or "",
                "price": float(offer["price"]) if offer.get("price") else None,
                "availability": "InStock" if "InStock" in avail else "OutOfStock",
            }
    return {}


def solo_author(meta):
    names = meta.get("authors") or []
    if len(names) != 1:
        return False
    return AUTHOR_SURNAME in names[0].lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/books-source.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    phrases = ["Владимир Маяковский", "Маяковский стихи", "Маяковский поэмы",
               "Маяковский пьесы", "Маяковский собрание сочинений",
               "Маяковский стихотворения и поэмы", "Маяковский детям"]
    candidates = {}
    author_page = None
    for i, phrase in enumerate(phrases):
        try:
            page = fetch(BASE + "/search?phrase=" + urllib.parse.quote(phrase))
        except Exception as e:  # noqa: BLE001
            print("поиск", phrase, "—", e)
            continue
        found = product_links(page)
        candidates.update({k: v for k, v in found.items() if k not in candidates})
        if author_page is None:
            m = re.search(r'href="(/author/[a-z0-9\-]+-\d+)"', page)
            author_page = m.group(1) if m else None
        print(f"{phrase}: +{len(found)} (всего {len(candidates)})")
        time.sleep(1.5)

    if author_page:
        for pageno in range(1, 6):
            url = BASE + author_page + ("" if pageno == 1 else f"?page={pageno}")
            try:
                page = fetch(url)
            except Exception as e:  # noqa: BLE001
                print("страница автора", pageno, "—", e)
                break
            found = product_links(page)
            new = {k: v for k, v in found.items() if k not in candidates}
            candidates.update(new)
            print(f"автор стр.{pageno}: +{len(new)} (всего {len(candidates)})")
            if not new:
                break
            time.sleep(1.5)

    ids = list(candidates.items())
    if args.limit:
        ids = ids[: args.limit]
    print(f"кандидатов: {len(ids)}")

    rows, by_isbn, skipped = [], {}, 0
    for i, (pid, href) in enumerate(ids, 1):
        url = BASE + href
        try:
            meta = book_meta(fetch(url))
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(ids)}] {pid} ошибка: {e}")
            continue
        title = meta.get("title") or ""
        if not meta or not solo_author(meta) or any(w in title.lower() for w in MERCH):
            skipped += 1
            continue
        row = {
            "id": pid,
            "url": url,
            "slug": href.rsplit("/", 1)[-1].rsplit("-", 1)[0],
            "title": re.sub(r"\s+", " ", title).strip(),
            "publisher": meta["publisher"],
            "isbn": meta["isbn"],
            "pages": meta["pages"],
            "price": meta["price"],
            "availability": meta["availability"],
            "price_checked": time.strftime("%Y-%m-%d"),
            "image": meta["image"],
        }
        key = row["isbn"] or f"{row['title']}|{row['pages']}"
        prev = by_isbn.get(key)
        better = (row["availability"] == "InStock", -(row["price"] or 10 ** 9))
        if not prev or better > (prev["availability"] == "InStock", -(prev["price"] or 10 ** 9)):
            by_isbn[key] = row
        print(f"[{i}/{len(ids)}] {pid} {row['title'][:52]:<52} {row['price']} {row['availability']}")
        time.sleep(1.2)

    rows = list(by_isbn.values())
    json.dump(rows, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    instock = sum(1 for r in rows if r["availability"] == "InStock")
    print(f"\nуникальных изданий: {len(rows)}, в наличии: {instock}, отброшено: {skipped} → {args.out}")


if __name__ == "__main__":
    main()
