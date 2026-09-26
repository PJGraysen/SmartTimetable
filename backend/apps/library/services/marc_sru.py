"""
SRU / MARC21 cataloguing client.

Primary source: Library of Congress SRU using the bath.isbn index.
Fallback: LoC dc.isbn.

MARCXML is parsed with xml.etree (no pymarc dependency).
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict


MARC_NS = "http://www.loc.gov/MARC21/slim"
MARC = {"marc": MARC_NS}

SRU_ENDPOINTS = [
    ("LoC bath.isbn",
     "http://lx2.loc.gov:210/lcdb?version=1.1&operation=searchRetrieve"
     "&query=bath.isbn%3D{isbn}&maximumRecords=1&recordSchema=marcxml"),
    ("LoC dc.isbn",
     "http://lx2.loc.gov:210/lcdb?version=1.1&operation=searchRetrieve"
     "&query=dc.isbn%3D{isbn}&maximumRecords=1&recordSchema=marcxml"),
]


@dataclass
class MarcLookupResult:
    isbn: str = ""
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
    marc21: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_isbn(isbn: str) -> str:
    return "".join(c for c in (isbn or "") if c.isdigit() or c in "Xx").upper()


def _http_get(url: str, timeout: float = 12.0) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTimetablePro/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _marcxml_to_dict(record_el) -> dict:
    out = {"leader": "", "fields": []}
    leader = record_el.find(f"{{{MARC_NS}}}leader")
    if leader is not None and leader.text:
        out["leader"] = leader.text.strip()
    for cf in record_el.findall(f"{{{MARC_NS}}}controlfield"):
        out["fields"].append({"tag": cf.get("tag"), "value": (cf.text or "").strip()})
    for df in record_el.findall(f"{{{MARC_NS}}}datafield"):
        subs = [
            {"code": sf.get("code"), "value": (sf.text or "").strip()}
            for sf in df.findall(f"{{{MARC_NS}}}subfield")
        ]
        out["fields"].append({
            "tag": df.get("tag"), "ind1": df.get("ind1", ""),
            "ind2": df.get("ind2", ""), "subfields": subs,
        })
    return out


def _field_get(marc_dict: dict, tag: str, code: str | None = None) -> str:
    for f in marc_dict.get("fields", []):
        if f.get("tag") != tag:
            continue
        if code is None:
            return f.get("value", "")
        for sf in f.get("subfields", []):
            if sf.get("code") == code:
                return sf.get("value", "")
    return ""


def _field_get_all(marc_dict: dict, tag: str, code: str) -> list[str]:
    out = []
    for f in marc_dict.get("fields", []):
        if f.get("tag") != tag:
            continue
        for sf in f.get("subfields", []):
            if sf.get("code") == code:
                out.append(sf.get("value", ""))
    return out


def _parse_marc(marc_dict: dict, isbn: str) -> MarcLookupResult:
    r = MarcLookupResult(isbn=isbn, marc21=marc_dict)

    title_a = _field_get(marc_dict, "245", "a")
    title_b = _field_get(marc_dict, "245", "b")
    r.title = title_a.rstrip(" /:;,")
    r.subtitle = title_b.rstrip(" /:;,.")

    authors = []
    a = _field_get(marc_dict, "100", "a")
    if a:
        authors.append(a.rstrip(" ,."))
    for a in _field_get_all(marc_dict, "700", "a"):
        a = a.rstrip(" ,.")
        if a and a not in authors:
            authors.append(a)
    r.authors = authors

    publisher = _field_get(marc_dict, "260", "b") or _field_get(marc_dict, "264", "b")
    r.publisher = publisher.rstrip(" ,:;.")

    year = _field_get(marc_dict, "260", "c") or _field_get(marc_dict, "264", "c")
    m = re.search(r"\b(1[5-9]\d{2}|2[01]\d{2})\b", year or "")
    if m:
        r.published_year = int(m.group(1))

    r.edition = _field_get(marc_dict, "250", "a").rstrip(" ,.")

    lang = _field_get(marc_dict, "041", "a")
    if lang:
        r.language = lang.strip()
    else:
        f008 = _field_get(marc_dict, "008")
        if len(f008 or "") >= 38:
            r.language = f008[35:38].strip()

    r.description = _field_get(marc_dict, "520", "a")
    pages = _field_get(marc_dict, "300", "a")
    if pages:
        pm = re.search(r"(\d+)", pages)
        if pm:
            r.page_count = int(pm.group(1))

    ddc_raw = _field_get(marc_dict, "082", "a")
    if ddc_raw:
        r.ddc = ddc_raw.split()[0]
    lcc_a = _field_get(marc_dict, "050", "a")
    lcc_b = _field_get(marc_dict, "050", "b")
    r.lcc = (lcc_a + " " + lcc_b).strip()

    r.toc = _field_get(marc_dict, "505", "a")

    isbn_020 = _field_get(marc_dict, "020", "a")
    if isbn_020:
        cleaned = _clean_isbn(isbn_020)
        if cleaned:
            r.isbn = cleaned

    r.source_id = _field_get(marc_dict, "001")
    return r


def lookup_marc_by_isbn(isbn: str) -> MarcLookupResult | None:
    cleaned = _clean_isbn(isbn)
    if len(cleaned) not in (10, 13):
        return None

    for label, template in SRU_ENDPOINTS:
        url = template.format(isbn=urllib.parse.quote(cleaned))
        xml = _http_get(url)
        if not xml:
            continue
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        records = root.findall(f".//{{{MARC_NS}}}record")
        if not records:
            continue
        marc_dict = _marcxml_to_dict(records[0])
        result = _parse_marc(marc_dict, cleaned)
        result.source = f"SRU:{label}"
        return result
    return None
