"""Build the buyer-facing comparison: markdown + csv, with provenance."""
import csv
import datetime as dt
import json
import os


def _money(x):
    return f"${x:,.2f}" if isinstance(x, (int, float)) else "not stated"


def build(brief, venues, quotes, out_dir="reports"):
    os.makedirs(out_dir, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    md_path = os.path.join(out_dir, f"quotes-{stamp}.md")
    csv_path = os.path.join(out_dir, f"quotes-{stamp}.csv")

    by_name = {}
    for q in quotes:
        by_name.setdefault(q["venue"], []).append(q)

    lines = [f"# Quote comparison — {brief['event']}", "",
             f"- Date needed: **{brief['date']}**",
             f"- Headcount: **{brief['headcount']}**",
             f"- Budget target: **{brief.get('budget_per_head') or 'open'}** per head",
             f"- Dietary: **{brief.get('dietary') or 'none specified'}**",
             f"- Providers contacted: **{sum(1 for v in venues if v.get('email'))}** of {len(venues)} discovered",
             f"- Replies parsed: **{len(quotes)}**",
             f"- Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
             "| Venue | Available | Price/head | Deposit / minimum | Dietary | Route | Evidence |",
             "|---|---|---|---|---|---|---|"]
    rows = []
    for v in venues:
        qs = by_name.get(v["name"], [])
        if qs:
            q = qs[0]
            lines.append("| {name} | {av} | {pr} | {dep} | {diet} | email reply | {ev} |".format(
                name=v["name"], av={True: "yes", False: "no", None: "not stated"}[q["available"]],
                pr=_money(q["price"]) + (" /head" if q.get("per_head") else ""),
                dep=(q.get("deposit_note") or "-"), diet=", ".join(q.get("dietary") or []) or "-",
                ev=(q.get("subject") or "")[:40].replace("|", "/")))
            rows.append([v["name"], q["available"], q["price"], q["per_head"], q.get("deposit_note"),
                         ";".join(q.get("dietary") or []), "email", q["email"]])
        else:
            lines.append(f"| {v['name']} | — | — | — | — | {v.get('contact_route')} | no reply yet |")
            rows.append([v["name"], None, None, None, None, None, v.get("contact_route"), v.get("email")])

    ranked = [r for r in rows if r[2] is not None]
    if ranked:
        ranked.sort(key=lambda r: r[2])
        lines += ["", "## Shortlist (cheapest confirmed first)", ""]
        for r in ranked[:5]:
            lines.append(f"1. **{r[0]}** — {_money(r[2])}{' /head' if r[3] else ''}"
                         f"{'; ' + r[4] if r[4] else ''} — contact {r[7] or 'n/a'}")
    lines += ["", "## How to read this", "",
              "- A price only appears if it was written in a reply; blanks are 'not stated', never estimated.",
              "- Route tells you how the provider was reached: email reply, public form, or phone (call sheet).",
              "- Every row traces to a mailbox message; the enquiry text sent is in outreach_log.jsonl."]

    open(md_path, "w").write("\n".join(lines) + "\n")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["venue", "available", "price", "per_head", "deposit_note", "dietary", "route", "email"])
        w.writerows(rows)
    return md_path, csv_path


def save_json(obj, path):
    json.dump(obj, open(path, "w"), indent=1)
    return path
