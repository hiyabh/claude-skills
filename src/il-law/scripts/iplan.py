"""Israel Planning Administration (iplan) - statutory plans via the public ArcGIS layer.

  iplan.py plan --number "101-0178129"
  iplan.py plans --name "רוממה" [--city "ירושלים"] [--limit 10]
  iplan.py query --where "plan_county_name = 'ירושלים' AND pl_date_8 > date '2025-01-01'" [--limit 20]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

LAYER = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/1"
QUERY_URL = LAYER + "/query"
DEFAULT_LIMIT = 10
FIELDS = ",".join([
    "pl_number", "pl_name", "mp_id", "plan_county_name", "district_name", "ja_concat",
    "internet_short_status", "station_desc", "entity_subtype_desc", "pl_area_dunam",
    "pl_landuse_string", "depositing_date", "pl_date7", "pl_date_8", "last_update_date",
    "pq_authorised_quantity_120", "pl_url", "pl_objectives",
])
DATE_FIELDS = {"depositing_date", "pl_date7", "pl_date_8", "last_update_date"}
MS_PER_S = 1000
DATE_LABELS = {"depositing_date": "deposit_hearing", "pl_date7": "approval_hearing",
               "pl_date_8": "published_in_reshumot", "last_update_date": "last_update"}


def quote(text):
    return text.replace("'", "''")


def to_date(value):
    from datetime import datetime, timezone

    if value is None:
        return None
    return datetime.fromtimestamp(value / MS_PER_S, tz=timezone.utc).strftime("%Y-%m-%d")


def slim(feature):
    attrs = feature["attributes"]
    row = {k: v for k, v in attrs.items() if k not in DATE_FIELDS}
    for field, label in DATE_LABELS.items():
        row[label] = to_date(attrs.get(field))
    return row


def query(where, limit):
    params = {"where": where, "outFields": FIELDS, "returnGeometry": "false",
              "resultRecordCount": str(limit), "orderByFields": "last_update_date DESC", "f": "json"}
    data = net.get_json(QUERY_URL, params=params)
    if "error" in data:
        raise net.SourceError("http_error", f"ArcGIS error: {data['error']}", QUERY_URL)
    net.require(data, ["features"], QUERY_URL)
    if data.get("exceededTransferLimit"):
        net.warn("more plans match than shown - narrow the query or raise --limit")
    return [slim(f) for f in data["features"]]


def cmd_plan(args):
    rows = query(f"pl_number = '{quote(args.number)}'", DEFAULT_LIMIT)
    if not rows:
        raise net.SourceError("not_found", f"no plan numbered {args.number} in the online-plans layer", QUERY_URL)
    return net.envelope(rows, QUERY_URL, net.AUTH_OFFICIAL)


def cmd_plans(args):
    where = f"pl_name LIKE '%{quote(args.name)}%'"
    if args.city:
        where += f" AND plan_county_name LIKE '%{quote(args.city)}%'"
    rows = query(where, args.limit)
    return net.envelope(rows, QUERY_URL, net.AUTH_OFFICIAL, count=len(rows))


def cmd_query(args):
    rows = query(args.where, args.limit)
    return net.envelope(rows, QUERY_URL, net.AUTH_OFFICIAL, count=len(rows))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--number", required=True)
    plan.set_defaults(func=cmd_plan)
    plans = sub.add_parser("plans")
    plans.add_argument("--name", required=True)
    plans.add_argument("--city")
    plans.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    plans.set_defaults(func=cmd_plans)
    raw = sub.add_parser("query")
    raw.add_argument("--where", required=True, help="ArcGIS SQL where clause")
    raw.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    raw.set_defaults(func=cmd_query)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    net.run(main)
