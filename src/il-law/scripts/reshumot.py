"""Reshumot - the official gazette (api.justice.gov.il/reshumot).

Authoritative published text of statutes (ס"ח), regulations (ק"ת), notices
(י"פ) and bills. Undocumented front-end API - modest volume only.

  reshumot.py series
  reshumot.py search --text "מקרקעין" [--series statuteBook] [--content] [--page 0]
  reshumot.py issue --id "/officialGazette/statuteBook/3579"
  reshumot.py pdf --path "akn/il/officialGazette/statuteBook/3579/heb@2026-08-02" [--out sh3579.pdf] [--max-chars 4000]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

BASE = "https://api.justice.gov.il/reshumot"
PORTAL = "https://reshumot.justice.gov.il"
HEADERS = {"User-Agent": net.BROWSER_UA, "Origin": PORTAL, "Referer": PORTAL + "/"}
PAGE_SIZE = 50  # fixed by the server
LANG = "heb"
DEFAULT_TEXT_CHARS = 4000
SERIES_HINT = "statuteBook=ס\"ח  generalSL=ק\"ת  publicNotices=י\"פ  governmentBills=הצ\"ח ממשלה  newVersionLaws=נוסח חדש"


def portal_link(issue_id):
    return f"{PORTAL}/#/view{issue_id}"


def cmd_series(args):
    url = BASE + "/akn-document-types"
    data = net.get_json(url, headers=HEADERS)
    net.require(data, ["documents"], url)
    rows = [{"short_name": d["short_name"], "hebrew": d["hebrew_name"], "abbrev": d["hebrew_short_name"]}
            for d in data["documents"]]
    return net.envelope(rows, url, net.AUTH_OFFICIAL)


def toc_rows(lang_data):
    return [{"title": t["publicationName"], "page": t.get("pageNumber"),
             "amends": [r["publicationName"] for r in t.get("references", [])]}
            for t in lang_data.get("tableOfContent") or []]


def slim_portfolio(p):
    data = p["data"] if "data" in p else p
    lang = data["languages"].get(LANG) or next(iter(data["languages"].values()))
    return {
        "id": data["ID"], "series": lang.get("seriesHebrewName"), "issue": data["magazineNumber"],
        "published": data["publishDate"], "hebrew_date": lang.get("publicationHebrewDate"),
        "pdf_path": lang["file"].lstrip("/"), "portal_url": portal_link(data["ID"]), "contents": toc_rows(lang),
    }


def cmd_search(args):
    url = BASE + "/search/portfolios"
    filters = {"seriesShortName": [args.series]} if args.series else {}
    body = {"freeText": args.text, "filters": filters, "page": args.page, "sort": {"publishDate": "desc"},
            "searchInContent": args.content, "lang": LANG}
    data = net.post_json(url, body, headers=HEADERS)
    net.require(data, ["total", "portfolios"], url)
    if not data["portfolios"] and "_event_transid" in data:
        raise net.SourceError("bad_payload", "search returned no payload (headers rejected?)", url)
    rows = [slim_portfolio(p) for p in data["portfolios"]]
    if data["total"] > (args.page + 1) * PAGE_SIZE:
        net.warn(f"{data['total']} issues match - use --page {args.page + 1} for more, or add --series")
    return net.envelope(rows, url, net.AUTH_OFFICIAL, total=data["total"], page=args.page)


def cmd_issue(args):
    url = BASE + "/official-gazette"
    data = net.get_json(url, params={"ID": args.id, "includePromulgationData": "true"}, headers=HEADERS)
    net.require(data, ["portfolios"], url)
    if not data["portfolios"]:
        raise net.SourceError("not_found", f"no gazette issue with id {args.id}", url)
    row = slim_portfolio(data["portfolios"][0])
    lang = data["portfolios"][0]["languages"][LANG]
    for toc, item in zip(row["contents"], lang.get("tableOfContent") or []):
        toc["amends"] = [f"{r['publicationName']} ({r.get('promulgationData', {}).get('details', '')})"
                         for r in item.get("references", [])]
    return net.envelope(row, url, net.AUTH_OFFICIAL)


def resolve_pdf(path):
    url = BASE + "/resolver"
    resp = net.request("GET", url, expect="bytes", params={"path": path}, headers=HEADERS, allow_redirects=False)
    location = resp.headers.get("Location")
    if resp.status_code != 302 or not location:
        raise net.SourceError("bad_payload", f"resolver answered HTTP {resp.status_code} without a redirect", url)
    return location


def cmd_pdf(args):
    signed = resolve_pdf(args.path.lstrip("/"))
    content = net.get_pdf(signed)
    text = net.pdf_text(content)
    data = {"pdf_bytes": len(content), "text_chars": len(text), "text": text[: args.max_chars],
            "note": "digit order in extracted Hebrew PDF text may be scrambled - verify quotes against the PDF"}
    if len(text) > args.max_chars:
        net.warn(f"text truncated to {args.max_chars} of {len(text)} chars - use --out and read the file")
    if args.out:
        data["saved"] = net.save_file(content, args.out)
    stable_url = f"{BASE}/resolver?path={args.path.lstrip('/')}"
    return net.envelope(data, stable_url, net.AUTH_OFFICIAL)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("series").set_defaults(func=cmd_series)
    search = sub.add_parser("search")
    search.add_argument("--text", required=True)
    search.add_argument("--series", help=SERIES_HINT)
    search.add_argument("--content", action="store_true", help="search inside documents, not only titles")
    search.add_argument("--page", type=int, default=0)
    search.set_defaults(func=cmd_search)
    issue = sub.add_parser("issue")
    issue.add_argument("--id", required=True, help='e.g. "/officialGazette/statuteBook/3579"')
    issue.set_defaults(func=cmd_issue)
    pdf = sub.add_parser("pdf")
    pdf.add_argument("--path", required=True, help="the pdf_path field from search/issue")
    pdf.add_argument("--out")
    pdf.add_argument("--max-chars", type=int, default=DEFAULT_TEXT_CHARS)
    pdf.set_defaults(func=cmd_pdf)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
