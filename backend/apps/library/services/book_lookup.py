
"""
Book metadata lookup: ISBN -> normalized fields.
Primary source: Open Library. Fallback: Google Books.
Pure HTTP; no DB writes. Callers persist.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict


@dataclass
class BookLookupResult:
    isbn: str
    title: str = ""
    subtitle: str = ""
    authors: list[str] = field(default_factory=list)
    publisher: str = ""
    published_year: int | None = None
    edition: str = ""
    language: str = ""
    description: str = ""
    cover_url: str = ""
    page_count: int | None = None
    ddc: str = ""
    lcc: str = ""
    toc: str = ""
    source: str = ""
    source_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_isbn(isbn: str) -> str:
    return "".join(c for c in (isbn or "") if c.isdigit() or c in "Xx").upper()


def _http_json(url: str, timeout: float = 8.0) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTimetablePro/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return None


def _lookup_openlibrary(isbn: str) -> BookLookupResult | None:
    url = f"https://openlibrary.org/isbn/{urllib.parse.quote(isbn)}.json"
    data = _http_json(url)
    if not data:
        return None
    r = BookLookupResult(isbn=isbn, source="OPENLIBRARY", source_id=str(data.get("key") or ""))
    r.title = str(data.get("title") or "")
    r.subtitle = str(data.get("subtitle") or "")
    # Authors: keys -> fetch each
    for ak in (data.get("authors") or [])[:5]:
        key = ak.get("key") if isinstance(ak, dict) else None
        if not key:
            continue
        a = _http_json(f"https://openlibrary.org{key}.json")
        if a and a.get("name"):
            r.authors.append(str(a["name"]))
    # Publishers
    pubs = data.get("publishers") or []
    if pubs:
        r.publisher = str(pubs[0])
    # Year
    pd = str(data.get("publish_date") or "")
    for token in pd.replace(",", " ").split():
        if token.isdigit() and len(token) == 4:
            r.published_year = int(token); break
    r.page_count = int(data.get("number_of_pages")) if data.get("number_of_pages") else None
    # Description (may be string or {value})
    desc = data.get("description")
    if isinstance(desc, dict): desc = desc.get("value")
    r.description = str(desc or "")
    # Classification
    r.ddc = str(data.get("dewey_decimal_class") or "")
    if isinstance(data.get("lc_classifications"), list) and data["lc_classifications"]:
        r.lcc = str(data["lc_classifications"][0])
    # Cover
    covers = data.get("covers") or []
    if covers:
        r.cover_url = f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"
    return r


def _lookup_googlebooks(isbn: str) -> BookLookupResult | None:
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{urllib.parse.quote(isbn)}"
    data = _http_json(url)
    if not data or not data.get("items"):
        return None
    item = data["items"][0]
    info = item.get("volumeInfo") or {}
    r = BookLookupResult(isbn=isbn, source="GOOGLEBOOKS", source_id=str(item.get("id") or ""))
    r.title = str(info.get("title") or "")
    r.subtitle = str(info.get("subtitle") or "")
    r.authors = [str(a) for a in (info.get("authors") or [])]
    r.publisher = str(info.get("publisher") or "")
    pd = str(info.get("publishedDate") or "")
    if pd[:4].isdigit():
        r.published_year = int(pd[:4])
    r.language = str(info.get("language") or "")
    r.description = str(info.get("description") or "")
    r.page_count = int(info.get("pageCount")) if info.get("pageCount") else None
    imgs = info.get("imageLinks") or {}
    r.cover_url = str(imgs.get("thumbnail") or "")
    return r


def lookup_by_isbn(isbn: str) -> BookLookupResult | None:
    cleaned = _clean_isbn(isbn)
    if len(cleaned) not in (10, 13):
        return None
    return _lookup_openlibrary(cleaned) or _lookup_googlebooks(cleaned)
