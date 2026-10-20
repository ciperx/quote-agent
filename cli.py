#!/usr/bin/env python3
"""quote-agent CLI.

  python cli.py demo --lat 39.7392 --lon -104.9903 --radius 12000 \
      --event "Team dinner" --date 2026-11-14 --headcount 24

  python cli.py send --brief brief.json --venues venues.json [--live]
  python cli.py parse --host imap.example.com --user u --password p --venues venues.json
"""
import argparse
import json
import os
import sys

from quoteagent import compose as C
from quoteagent import discover as D
from quoteagent import enrich as E
from quoteagent import parse as P
from quoteagent import report as R
from quoteagent import send as S

HERE = os.path.dirname(os.path.abspath(__file__))


def demo(a):
    brief = {"event": a.event, "date": a.date, "headcount": a.headcount,
             "budget_per_head": a.budget, "dietary": a.dietary, "privacy": a.privacy}
    venues = D.discover(a.lat, a.lon, radius_m=a.radius, limit=a.limit)
    print(f"discovered {len(venues)} providers", file=sys.stderr)
    enriched = []
    for v in venues[:a.enrich]:
        enriched.append(E.enrich(v))
    with_email = sum(1 for v in enriched if v.get("email"))
    print(f"reachable by email: {with_email}/{len(enriched)}", file=sys.stderr)
    msgs = [C.compose(v, brief) for v in enriched if v.get("email")]
    R.save_json(brief, os.path.join(HERE, "brief.json"))
    R.save_json(enriched, os.path.join(HERE, "venues.json"))
    R.save_json(msgs, os.path.join(HERE, "enquiries.json"))
    md, csvp = R.build(brief, enriched, [])
    print(f"report: {md}\ncsv: {csvp}\nenquiries drafted: {len(msgs)} (not sent)")
    return 0


def send(a):
    brief = json.load(open(a.brief))
    venues = json.load(open(a.venues))
    msgs = [C.compose(v, brief) for v in venues if v.get("email")]
    ok = 0
    for m in msgs[:a.limit]:
        res = S.send(m, dry_run=not a.live)
        ok += 1 if res.get("ok") else 0
        print(json.dumps(res)[:200])
    print(f"sent/ok {ok} of {min(len(msgs), a.limit)} (live={a.live})")
    return 0


def parse_cmd(a):
    venues = json.load(open(a.venues))
    replies = P.fetch(a.host, a.user, a.password, since_days=a.days)
    rows = P.match_to_venues(replies, venues)
    R.save_json(rows, os.path.join(HERE, "quotes.json"))
    print(f"replies {len(replies)} matched {len(rows)}")
    for r in rows:
        print(f"  {r['venue'][:30]:30} available={r['available']} price={r['price']} per_head={r['per_head']}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("demo")
    d.add_argument("--lat", type=float, default=39.7392)
    d.add_argument("--lon", type=float, default=-104.9903)
    d.add_argument("--radius", type=int, default=12000)
    d.add_argument("--limit", type=int, default=120)
    d.add_argument("--enrich", type=int, default=40)
    d.add_argument("--event", default="Group dinner")
    d.add_argument("--date", default="2026-11-14")
    d.add_argument("--headcount", type=int, default=24)
    d.add_argument("--budget", default=None)
    d.add_argument("--dietary", default=None)
    d.add_argument("--privacy", default=None)
    s = sub.add_parser("send")
    s.add_argument("--brief", required=True)
    s.add_argument("--venues", required=True)
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--live", action="store_true")
    p = sub.add_parser("parse")
    p.add_argument("--host", required=True)
    p.add_argument("--user", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--venues", required=True)
    p.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    if a.cmd == "demo":
        return demo(a)
    if a.cmd == "send":
        return send(a)
    if a.cmd == "parse":
        return parse_cmd(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
