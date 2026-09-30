"""Knesset OData v4 client: law register, validity, amendments, bills, secondary legislation.

The register holds metadata and links to published PDFs only - never the
consolidated text. For text use wikisrc.py, then confirm validity here.

  knesset.py search --name "התכנון והבנייה"
  knesset.py law --id 2000416 [--amendments 10]
  knesset.py bills --name "פינוי ובינוי" [--knesset 25]
  knesset.py secondary --name "התכנון והבנייה"
  knesset.py query --entity KNS_DocumentCommitteeSession --filter "contains(DocumentName,'מקרקעין')"
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

BASE = "https://knesset.gov.il/OdataV4/ParliamentInfo/"
PAGE_CAP = 100  # the server silently caps every page at 100 rows
DEFAULT_TOP = 20
DEFAULT_AMENDMENTS = 10
LAW_FIELDS = "Id,Name,KnessetNum,IsBasicLaw,LawValidityDesc,PublicationDate,LatestPublicationDate,ValidityFinishDate"
BILL_FIELDS = "Id,Name,KnessetNum,SubTypeDesc,StatusID,PublicationDate,PublicationSeriesDesc,MagazineNumber,PageNumber"
PUBLISHED_DOC_MARK = "פרסום ברשומות"
SPELLING_HINT = "0 results - try a spelling variant (e.g. בניה/בנייה, מקרקעין/מקרקעים) or a shorter phrase"


def quote(text):
    return text.replace("'", "''")


def clean_path(path):
    return path.replace("\\", "/") if path else path


def fetch(entity, params):
    url = BASE + entity
    data = net.get_json(url, params=params)
    net.require(data, ["value"], url)
    if len(data["value"]) == PAGE_CAP:
        net.warn(f"{entity}: page capped at {PAGE_CAP} rows - narrow the filter, more rows exist")
    return data["value"]


def slim_docs(docs):
    return [
        {"kind": d["GroupTypeDesc"], "format": d["ApplicationDesc"], "url": clean_path(d["FilePath"])}
        for d in docs
    ]


def search_by_name(entity, name, select, extra_filter="", expand="", top=DEFAULT_TOP):
    clause = f"contains(Name,'{quote(name)}')"
    if extra_filter:
        clause += f" and {extra_filter}"
    params = {"$filter": clause, "$orderby": "Id desc", "$top": str(top)}
    if select:
        params["$select"] = select
    if expand:
        params["$expand"] = expand
    rows = fetch(entity, params)
    if not rows:
        net.warn(SPELLING_HINT)
    return rows


def amending_bills(law_ids):
    """Amending laws are stored as bills that completed legislation."""
    clause = " or ".join(f"Id eq {i}" for i in law_ids)
    params = {"$filter": clause, "$select": BILL_FIELDS, "$expand": "KNS_DocumentBill"}
    return {b["Id"]: b for b in fetch("KNS_Bill", params)}


def amendment_row(binding, bill):
    row = {
        "amendment_number": binding["CorrectionNumber"],
        "type": binding["AmendmentTypeDesc"],
        "binding": binding["BindingTypeDesc"],
        "amending_law_id": binding["LawID"],
    }
    if not bill:
        row["note"] = "amending law not found in KNS_Bill - look it up in Reshumot"
        return row
    docs = slim_docs(bill["KNS_DocumentBill"])
    published = [d for d in docs if PUBLISHED_DOC_MARK in d["kind"]]
    row.update(
        name=bill["Name"].strip(),
        published=bill["PublicationDate"],
        gazette=f"{bill['PublicationSeriesDesc']} {bill['MagazineNumber']}, עמ' {bill['PageNumber']}",
        documents=published or docs,
    )
    return row


def law_amendments(law_id, limit):
    params = {"$filter": f"IsraelLawID eq {law_id}", "$orderby": "Id desc", "$top": str(limit), "$count": "true"}
    url = BASE + "KNS_LawBinding"
    data = net.get_json(url, params=params)
    net.require(data, ["value"], url)
    bindings = data["value"]
    bills = amending_bills([b["LawID"] for b in bindings]) if bindings else {}
    rows = [amendment_row(b, bills.get(b["LawID"])) for b in bindings]
    return data.get("@odata.count", len(rows)), rows


def cmd_law(args):
    url = f"{BASE}KNS_IsraelLaw({args.id})"
    law = net.get_json(url, params={"$select": LAW_FIELDS})
    net.require(law, ["Name", "LawValidityDesc"], url)
    total, amendments = law_amendments(args.id, args.amendments)
    data = {"law": law, "bindings_total": total, "latest_amendments": amendments}
    return net.envelope(data, url, net.AUTH_METADATA)


def cmd_search(args):
    rows = search_by_name("KNS_IsraelLaw", args.name, LAW_FIELDS, top=args.top)
    return net.envelope(rows, BASE + "KNS_IsraelLaw", net.AUTH_METADATA)


def cmd_bills(args):
    extra = f"KnessetNum eq {args.knesset}" if args.knesset else ""
    rows = search_by_name("KNS_Bill", args.name, BILL_FIELDS, extra, "KNS_DocumentBill", args.top)
    for row in rows:
        row["documents"] = slim_docs(row.pop("KNS_DocumentBill"))
    return net.envelope(rows, BASE + "KNS_Bill", net.AUTH_OFFICIAL)


def cmd_secondary(args):
    rows = search_by_name("KNS_SecondaryLaw", args.name, "", "", "KNS_DocumentSecondaryLaw", args.top)
    for row in rows:
        row["documents"] = slim_docs(row.pop("KNS_DocumentSecondaryLaw"))
    return net.envelope(rows, BASE + "KNS_SecondaryLaw", net.AUTH_OFFICIAL)


def cmd_query(args):
    params = {"$top": str(args.top)}
    for key, value in (("$filter", args.filter), ("$select", args.select), ("$orderby", args.orderby)):
        if value:
            params[key] = value
    rows = fetch(args.entity, params)
    for row in rows:
        if "FilePath" in row:
            row["FilePath"] = clean_path(row["FilePath"])
    return net.envelope(rows, BASE + args.entity, net.AUTH_OFFICIAL)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    law = sub.add_parser("law", help="law record, validity and latest amendments")
    law.add_argument("--id", type=int, required=True)
    law.add_argument("--amendments", type=int, default=DEFAULT_AMENDMENTS)
    law.set_defaults(func=cmd_law)
    for name, func in (("search", cmd_search), ("bills", cmd_bills), ("secondary", cmd_secondary)):
        cmd = sub.add_parser(name)
        cmd.add_argument("--name", required=True)
        cmd.add_argument("--top", type=int, default=DEFAULT_TOP)
        cmd.set_defaults(func=func)
    sub.choices["bills"].add_argument("--knesset", type=int)
    query = sub.add_parser("query", help="raw OData v4 query on any entity set")
    query.add_argument("--entity", required=True)
    for flag in ("--filter", "--select", "--orderby"):
        query.add_argument(flag)
    query.add_argument("--top", type=int, default=DEFAULT_TOP)
    query.set_defaults(func=cmd_query)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
