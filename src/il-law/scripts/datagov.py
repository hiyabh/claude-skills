"""data.gov.il (CKAN) - government open data relevant to legal and real-estate work.

  datagov.py datasets --q "שמאי מכריע"
  datagov.py fields --resource c4e178ff-9038-45f4-9dd1-fe7aeea6f70c
  datagov.py rows --resource <id> [--q "היטל השבחה"] [--filter block=6158] [--limit 20]
  datagov.py samay --q "ירושלים" [--limit 10]          (decisive-appraiser determinations, PDF links)
  datagov.py samay-pdf --url "<link from samay>" [--out x.pdf] [--max-chars 3000]
  datagov.py company --q "שם החברה"                      (companies registry)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

BASE = "https://data.gov.il/api/3/action/"
DATASET_PAGE = "https://data.gov.il/dataset/"
RESOURCES = {
    "samay": "c4e178ff-9038-45f4-9dd1-fe7aeea6f70c",     # מאגר נתוני שמאות מכריעה (משרד המשפטים)
    "companies": "f004176c-b85f-4542-8901-7b3176f9a054",  # רשם החברות
    "ararim": "b9580b33-6b41-4ca3-b6e1-eb4bbf96a318",     # החלטות בית הדין לעררים
    "regulation_index": "929b4c60-ce43-4f5b-9960-f6146ba33eed",  # מאגר האסדרה: חוק -> ויקיטקסט/כנסת
}
PDF_HOST = "https://free-justice.openapi.gov.il/"
DEFAULT_LIMIT = 20
DEFAULT_TEXT_CHARS = 3000
MAX_FIELD_LEN = 300


def action(name, params):
    url = BASE + name
    data = net.get_json(url, params=params)
    net.require(data, ["success", "result"], url)
    if not data["success"]:
        raise net.SourceError("http_error", f"CKAN {name} failed: {data.get('error')}", url)
    return data["result"], url


def parse_filters(pairs):
    filters = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        filters[key] = value
    return filters


def trim(record):
    return {k: (v[:MAX_FIELD_LEN] if isinstance(v, str) else v) for k, v in record.items() if k != "_id"}


def datastore(resource, q="", filters=None, limit=DEFAULT_LIMIT):
    import json

    params = {"resource_id": resource, "limit": str(limit)}
    if q:
        params["q"] = q
    if filters:
        params["filters"] = json.dumps(filters, ensure_ascii=False)
    result, url = action("datastore_search", params)
    total = result.get("total", 0)
    if total > limit:
        net.warn(f"{total} rows match - showing {limit}; add --filter or a narrower --q")
    return [trim(r) for r in result["records"]], total, url


def cmd_datasets(args):
    result, url = action("package_search", {"q": args.q, "rows": str(args.limit)})
    rows = [{"name": p["name"], "title": p["title"], "org": p.get("organization", {}).get("title"),
             "updated": p.get("metadata_modified", "")[:10], "page": DATASET_PAGE + p["name"],
             "resources": [{"id": r["id"], "name": r.get("name"), "format": r.get("format")} for r in p["resources"]]}
            for p in result["results"]]
    return net.envelope(rows, url, net.AUTH_OFFICIAL, total=result["count"])


def cmd_fields(args):
    result, url = action("datastore_search", {"resource_id": args.resource, "limit": "1"})
    fields = [f["id"] for f in result["fields"] if f["id"] != "_id"]
    return net.envelope({"fields": fields, "sample": [trim(r) for r in result["records"]]}, url, net.AUTH_OFFICIAL)


def cmd_rows(args):
    rows, total, url = datastore(args.resource, args.q, parse_filters(args.filter), args.limit)
    return net.envelope(rows, url, net.AUTH_OFFICIAL, total=total)


def cmd_samay(args):
    rows, total, url = datastore(RESOURCES["samay"], args.q, parse_filters(args.filter), args.limit)
    net.warn("each row's 'link' is a directly downloadable official PDF - fetch with: samay-pdf --url")
    return net.envelope(rows, url, net.AUTH_OFFICIAL, total=total)


def cmd_samay_pdf(args):
    if not args.url.startswith(PDF_HOST):
        raise net.SourceError("host_not_allowed", f"expected a {PDF_HOST} link from the samay dataset", args.url)
    content = net.get_pdf(args.url)
    text = net.pdf_text(content)
    data = {"pdf_bytes": len(content), "text_chars": len(text), "text": text[: args.max_chars]}
    if args.out:
        data["saved"] = net.save_file(content, args.out)
    return net.envelope(data, args.url, net.AUTH_OFFICIAL)


def cmd_company(args):
    rows, total, url = datastore(RESOURCES["companies"], args.q, None, args.limit)
    return net.envelope(rows, url, net.AUTH_OFFICIAL, total=total)


def add_query_flags(cmd, with_filter=True):
    cmd.add_argument("--q", default="")
    cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    if with_filter:
        cmd.add_argument("--filter", action="append", help="exact match, e.g. --filter block=6158")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    datasets = sub.add_parser("datasets")
    add_query_flags(datasets, with_filter=False)
    datasets.set_defaults(func=cmd_datasets)
    fields = sub.add_parser("fields")
    fields.add_argument("--resource", required=True)
    fields.set_defaults(func=cmd_fields)
    rows = sub.add_parser("rows")
    rows.add_argument("--resource", required=True)
    add_query_flags(rows)
    rows.set_defaults(func=cmd_rows)
    samay = sub.add_parser("samay")
    add_query_flags(samay)
    samay.set_defaults(func=cmd_samay)
    samay_pdf = sub.add_parser("samay-pdf")
    samay_pdf.add_argument("--url", required=True)
    samay_pdf.add_argument("--out")
    samay_pdf.add_argument("--max-chars", type=int, default=DEFAULT_TEXT_CHARS)
    samay_pdf.set_defaults(func=cmd_samay_pdf)
    company = sub.add_parser("company")
    add_query_flags(company, with_filter=False)
    company.set_defaults(func=cmd_company)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
