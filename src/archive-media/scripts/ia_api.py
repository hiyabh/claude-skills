"""Shared helpers for archive-media: polite HTTP to archive.org, search, metadata, rights grading.

No API key and no third-party packages - standard library only.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://archive.org/advancedsearch.php"
METADATA_URL = "https://archive.org/metadata/{}"
DOWNLOAD_URL = "https://archive.org/download/{}/{}"
DETAILS_URL = "https://archive.org/details/{}"
USER_AGENT = "claude-archive-media/1.0 (+https://github.com/hiyabh/claude-skills)"
TIMEOUT_S = 30
RETRIES = 3
BACKOFF_S = 2.0
POLITE_DELAY_S = 0.5

# US rule (verified 2026-10-26): recordings published through 1925 entered the public domain on 2026-01-01.
# Each January 1st one more year enters, so the cutoff is current_year - 101.
PD_RECORDING_LAST_YEAR = time.localtime().tm_year - 101

PRESETS = {
    "prelinger": {"collection": "prelinger", "mediatype": "movies"},
    "78rpm": {"collection": "georgeblood", "mediatype": "audio"},
    "live": {"collection": "etree", "mediatype": "etree"},
    "any": {"collection": None, "mediatype": None},
}
SEARCH_FIELDS = ["identifier", "title", "year", "date", "licenseurl", "runtime",
                 "creator", "downloads", "collection", "mediatype"]

GREEN, YELLOW, RED = "🟢", "🟡", "🔴"
PD_MARKERS = ("publicdomain", "/zero/", "/mark/")


def http_get_json(url, params=None):
    """GET a JSON document with retries and exponential backoff."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                time.sleep(POLITE_DELAY_S)
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            time.sleep(BACKOFF_S * (2 ** attempt))
    raise RuntimeError(f"archive.org request failed after {RETRIES} tries: {url}\n{last_err}\n"
                       "Check the network connection and https://archive.org status, then retry.")


def build_query(text, preset, years=None, cleared_only=False):
    """Compose an advancedsearch Lucene query from the user's words and filters."""
    spec = PRESETS[preset]
    parts = [f"({text})"] if text else []
    if spec["collection"]:
        parts.append(f"collection:{spec['collection']}")
    if spec["mediatype"]:
        parts.append(f"mediatype:{spec['mediatype']}")
    if years:
        parts.append(f"year:[{years[0]} TO {years[1]}]")
    if cleared_only and preset != "78rpm":
        parts.append("licenseurl:*")
    return " AND ".join(parts) or "*:*"


def advanced_search(query, rows=25, sort="downloads desc"):
    """Run an advancedsearch query; returns (total_found, docs)."""
    params = {"q": query, "fl[]": SEARCH_FIELDS, "rows": rows, "page": 1,
              "output": "json", "sort[]": sort}
    data = http_get_json(SEARCH_URL, params)
    resp = data.get("response", {})
    return resp.get("numFound", 0), resp.get("docs", [])


def item_metadata(identifier):
    """Full item record (metadata + file list)."""
    data = http_get_json(METADATA_URL.format(urllib.parse.quote(identifier)))
    if not data or "metadata" not in data:
        raise RuntimeError(f"Item '{identifier}' not found on archive.org. Check the identifier spelling.")
    return data


def download_url(identifier, filename):
    return DOWNLOAD_URL.format(urllib.parse.quote(identifier), urllib.parse.quote(filename))


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def item_year(doc):
    """Year from the 'year' field, falling back to the first 4 digits of 'date'."""
    for key in ("year", "date"):
        raw = str(as_list(doc.get(key))[0]) if doc.get(key) else ""
        if raw[:4].isdigit():
            return int(raw[:4])
    return None


def _grade_license(lic):
    if any(m in lic for m in PD_MARKERS):
        return GREEN, "רשות הציבור / CC0 לפי הרישיון המסומן"
    if "-nc" in lic or "/nc" in lic:
        return RED, "רישיון CC לא-מסחרי (NC) - אסור בפרסומת או בתוכן מסחרי"
    if "-nd" in lic:
        return RED, "רישיון CC ללא יצירות נגזרות (ND) - אסור לחתוך ולשלב בעריכה"
    if "creativecommons.org/licenses/by" in lic:
        return GREEN, "CC BY / BY-SA - מותר, ייחוס חובה"
    return YELLOW, f"רישיון לא מזוהה ({lic}) - לבדוק ידנית"


def _grade_recording(year):
    if year is None:
        return YELLOW, "78 סל\"ד בלי שנה - לא ניתן לקבוע זכויות"
    if year <= PD_RECORDING_LAST_YEAR:
        return GREEN, (f"הקלטה משנת {year}: רשות הציבור בארה\"ב (עד {PD_RECORDING_LAST_YEAR}). "
                       "סיכון Content ID ביוטיוב; הלחן או העיבוד עשויים להיות מוגנים")
    return RED, f"הקלטה משנת {year}: עדיין מוגנת בארה\"ב (אחרי {PD_RECORDING_LAST_YEAR})"


def rights_grade(doc):
    """Return (emoji, Hebrew reason) for an item's reuse rights in an edit."""
    collections = as_list(doc.get("collection"))
    lic = str(as_list(doc.get("licenseurl"))[0]).lower() if doc.get("licenseurl") else ""
    if "etree" in collections or doc.get("mediatype") == "etree":
        return RED, "הופעה חיה (Live Music Archive) - לשימוש לא-מסחרי בלבד לפי מדיניות האמנים"
    if lic:
        return _grade_license(lic)
    if "georgeblood" in collections or "78rpm" in collections:
        return _grade_recording(item_year(doc))
    return YELLOW, "אין רישיון מסומן - ייתכן שמוגן; לחפש עותק מורשה, או לקבל החלטה מפורשת לפני מסירה"
