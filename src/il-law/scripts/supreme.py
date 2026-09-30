"""Supreme Court of Israel decisions (supremedecisions.court.gov.il).

Uses the site's own undocumented JSON backend. Keep volume low: one search,
then fetch only the rulings actually needed. Quote only text that was fetched.

  supreme.py search --text "דייר סרבן" [--from 2020-01-01] [--to 2026-09-30] [--type verdict]
  supreme.py case --num 1234 --year 2020
  supreme.py get --path "<path>" --file "<file>" [--max-chars 6000] [--offset 6000] [--out ruling.pdf]
"""
import argparse
import os
import sys
from datetime import date
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

SITE = "https://supremedecisions.court.gov.il"
SEARCH_URL = SITE + "/Home/SearchVerdicts"
DOWNLOAD_URL = SITE + "/Home/Download"
HEADERS = {
    "User-Agent": net.BROWSER_UA,
    "Referer": SITE + "/",
    "Origin": SITE,
    "X-Requested-With": "XMLHttpRequest",
}
FILE_TYPE_PDF = 4
FILE_TYPE_HTML = 2
MIN_HTML_BYTES = 2000
DATE_TYPE_RULING = 2  # 1 = publication date, which does not filter old rulings reliably
PUBLISH_DATE_MODE = 8
LANG_HEBREW = 1
RESULT_CAP = 500
DEFAULT_FROM = "1948-01-01"
DEFAULT_TOP = 25
DEFAULT_TEXT_CHARS = 6000
TYPE_FILTERS = {"verdict": "פסק-דין", "decision": "החלטה"}
ROW_KEYS = ["CaseDesc", "PathForWeb", "FileName"]

_primed = False


def prime():
    """The backend only answers a session that first loaded the home page."""
    global _primed
    if not _primed:
        net.request("GET", SITE + "/", expect="text", headers={"User-Agent": net.BROWSER_UA})
        _primed = True


def text_term(text):
    return {"Text": text, "textOperator": 1, "option": 2, "Inverted": False,
            "Synonym": False, "NearDistance": 3, "MatchOrder": False}


def search_body(text, date_from, date_to, year=None, case_num=None):
    document = {
        "Year": year, "CaseNum": case_num, "dateType": DATE_TYPE_RULING,
        "publishDate": PUBLISH_DATE_MODE, "SearchText": [text_term(text)] if text else [],
        "PublishFrom": f"{date_from}T00:00:00.000Z", "PublishTo": f"{date_to}T00:00:00.000Z",
        "Month": None, "OldMainNumFormat": False,
    }
    return {"document": document, "lan": LANG_HEBREW}


def download_link(row):
    query = urlencode({"path": row["PathForWeb"], "fileName": row["FileName"], "type": FILE_TYPE_PDF})
    return f"{DOWNLOAD_URL}?{query}"


def slim(row):
    net.require(row, ROW_KEYS, SEARCH_URL)
    return {
        "case": row["CaseDesc"], "name": row.get("CaseName"), "type": row.get("Type"),
        "date": row.get("VerdictsDtString"), "pages": row.get("Pages"),
        "path": row["PathForWeb"], "file": row["FileName"], "pdf_url": download_link(row),
    }


def run_search(body, doc_type, top):
    prime()
    data = net.post_json(SEARCH_URL, body, headers=HEADERS)
    net.require(data, ["data"], SEARCH_URL)
    rows = data["data"] or []
    if len(rows) >= RESULT_CAP:
        net.warn(f"truncated: the backend caps results at {RESULT_CAP} - narrow the dates or the phrase")
    if doc_type != "all":
        rows = [r for r in rows if TYPE_FILTERS[doc_type] in (r.get("Type") or "")]
    shown = [slim(r) for r in rows[:top]]
    return net.envelope(shown, SEARCH_URL, net.AUTH_OFFICIAL, total_matches=len(rows), shown=len(shown))


def cmd_search(args):
    body = search_body(args.text, args.date_from, args.date_to)
    return run_search(body, args.type, args.top)


def cmd_case(args):
    body = search_body("", args.date_from, args.date_to, year=args.year, case_num=args.num)
    return run_search(body, "all", args.top)


def html_text(path, file_name):
    """The HTML rendition keeps logical RTL order; PDF extraction scrambles numbers."""
    from bs4 import BeautifulSoup

    query = urlencode({"path": path, "fileName": file_name, "type": FILE_TYPE_HTML})
    resp = net.request("GET", f"{DOWNLOAD_URL}?{query}", expect="text", headers=HEADERS)
    if resp.status_code != 200 or len(resp.content) < MIN_HTML_BYTES:
        return None
    soup = BeautifulSoup(resp.content, "html.parser")
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def ruling_text(args, url):
    text = html_text(args.path, args.file)
    if text:
        return text, None
    net.warn("HTML rendition unavailable - text extracted from the PDF, digit order may be scrambled")
    content = net.get_pdf(url, headers=HEADERS)
    return net.pdf_text(content), content


def cmd_get(args):
    prime()
    url = download_link({"PathForWeb": args.path, "FileName": args.file})
    text, pdf = ruling_text(args, url)
    data = {"text_chars": len(text), "text": text[args.offset: args.offset + args.max_chars]}
    if args.offset + args.max_chars < len(text):
        net.warn(f"showing chars {args.offset}-{args.offset + args.max_chars} of {len(text)} - continue with --offset")
    if args.out:
        data["saved"] = net.save_file(pdf or net.get_pdf(url, headers=HEADERS), args.out)
    return net.envelope(data, url, net.AUTH_OFFICIAL)


def add_dates(cmd):
    cmd.add_argument("--from", dest="date_from", default=DEFAULT_FROM, help="ruling date, YYYY-MM-DD")
    cmd.add_argument("--to", dest="date_to", default=date.today().isoformat())
    cmd.add_argument("--top", type=int, default=DEFAULT_TOP)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    search = sub.add_parser("search")
    search.add_argument("--text", required=True)
    search.add_argument("--type", choices=["all", *TYPE_FILTERS], default="all")
    add_dates(search)
    search.set_defaults(func=cmd_search)
    case = sub.add_parser("case")
    case.add_argument("--num", type=int, required=True)
    case.add_argument("--year", type=int, required=True)
    add_dates(case)
    case.set_defaults(func=cmd_case)
    get = sub.add_parser("get")
    get.add_argument("--path", required=True)
    get.add_argument("--file", required=True)
    get.add_argument("--out")
    get.add_argument("--max-chars", type=int, default=DEFAULT_TEXT_CHARS)
    get.add_argument("--offset", type=int, default=0)
    get.set_defaults(func=cmd_get)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
