"""Verify a citation before it is delivered. Answers: found / not_found / unreachable, with the canonical link.

  cite.py law --id 2000416 [--title "חוק המקרקעין"]     validity + is the Wikisource text current?
  cite.py case --num 1642 --year 2024                     does this Supreme Court case exist? links
  cite.py url --url "https://fs.knesset.gov.il/25/law/25_lsr_3476058.pdf"   is the link live and a document?
"""
import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knesset
import net
import supreme
import wikisrc

VALID_MARK = "תקף"
SUPREME_LINK_PARTS = ("path=", "fileName=", "type=")
DOC_TYPES = ("application/pdf", "text/html", "application/msword", "application/vnd.openxmlformats")


def verdict(found, **fields):
    return {"verdict": "found" if found else "not_found", **fields}


def cmd_law(args):
    url = f"{knesset.BASE}KNS_IsraelLaw({args.id})"
    law = net.get_json(url, params={"$select": knesset.LAW_FIELDS})
    net.require(law, ["Name", "LawValidityDesc", "LatestPublicationDate"], url)
    result = verdict(True, law_id=args.id, name=law["Name"], validity=law["LawValidityDesc"],
                     in_force=law["LawValidityDesc"] == VALID_MARK,
                     latest_amendment_published=law["LatestPublicationDate"][:10], knesset_url=url)
    if args.title:
        result["wikisource"] = wikisource_status(args.title, args.id, law["LatestPublicationDate"][:10])
    return net.envelope(result, url, net.AUTH_METADATA)


def wikisource_status(title, law_id, latest_amendment):
    page_title, rev, wikitext = wikisrc.load_page(title)
    meta = wikisrc.page_meta(page_title, rev, wikitext)
    revised = meta["revision_timestamp"][:10]
    status = {"title": page_title, "revision": revised, "permalink": wikisrc.PERMALINK.format(revid=rev["revid"]),
              "same_law": meta["knesset_law_id"] == law_id}
    if not status["same_law"]:
        net.warn(f"Wikisource page carries Knesset id {meta['knesset_law_id']}, not {law_id} - wrong page?")
    status["text_current"] = revised >= latest_amendment
    if not status["text_current"]:
        net.warn(f"Wikisource revision {revised} predates the latest amendment ({latest_amendment}) - text may be stale")
    return status


def cmd_case(args):
    body = supreme.search_body("", supreme.DEFAULT_FROM, date.today().isoformat(), year=args.year, case_num=args.num)
    supreme.prime()
    data = net.post_json(supreme.SEARCH_URL, body, headers=supreme.HEADERS)
    rows = [supreme.slim(r) for r in (data.get("data") or [])]
    result = verdict(bool(rows), case_num=args.num, year=args.year, documents=rows,
                     searched="Supreme Court public decisions database only")
    return net.envelope(result, supreme.SEARCH_URL, net.AUTH_OFFICIAL)


def cmd_url(args):
    if args.url.startswith(supreme.DOWNLOAD_URL) and not all(p in args.url for p in SUPREME_LINK_PARTS):
        result = verdict(False, url=args.url, note="Supreme Court link is truncated - use pdf_url exactly as "
                         "supreme.py returned it (path + fileName + type)")
        return net.envelope(result, args.url, net.AUTH_OFFICIAL)
    headers = {"User-Agent": net.BROWSER_UA}
    resp = net.request("GET", args.url, expect="bytes", headers=headers, stream=True)
    ctype = resp.headers.get("Content-Type", "")
    is_doc = resp.status_code == 200 and any(ctype.startswith(t) for t in DOC_TYPES)
    resp.close()
    result = verdict(is_doc, url=args.url, http_status=resp.status_code, content_type=ctype)
    return net.envelope(result, args.url, net.AUTH_OFFICIAL)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    law = sub.add_parser("law")
    law.add_argument("--id", type=int, required=True)
    law.add_argument("--title", help="Wikisource page title to check for staleness")
    law.set_defaults(func=cmd_law)
    case = sub.add_parser("case")
    case.add_argument("--num", type=int, required=True)
    case.add_argument("--year", type=int, required=True)
    case.set_defaults(func=cmd_case)
    url = sub.add_parser("url")
    url.add_argument("--url", required=True)
    url.set_defaults(func=cmd_url)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
