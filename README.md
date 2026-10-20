# quote-agent

Collects real quotes from local businesses by contacting them, and returns one
comparison table. Built for group dining and local services sourcing.

No login, no API keys for discovery, no headless browser. Three moving parts:

1. **Discovery** — OpenStreetMap Overpass, queried by tag around a point.
   Returns name, address, phone, website, email, capacity, cuisine, OSM id.
2. **Enrichment** — for providers without an email tag, fetch the site's
   homepage and contact/about/catering pages and take the first `mailto:`
   address found. The URL it came from is recorded as provenance.
3. **Outreach** — one email per provider, asking exactly three closed
   questions (available on the date? price per head / minimum spend / deposit?
   dietary handling?). Sends through Resend from a verified domain, or SMTP if
   you prefer. Dry-run by default; `--live` sends.
4. **Reply parsing** — read-only IMAP, matches each reply to a venue by sender
   address and extracts availability, price, per-head flag, deposit/minimum note
   and dietary mentions. Nothing is inferred: missing values stay `null` and the
   report prints "not stated".
5. **Report** — markdown table plus CSV, with a provenance column and a
   cheapest-confirmed shortlist.

## Why it is built this way

- **Provenance everywhere.** A price is only shown if a reply stated it; the
  enquiry that produced it is in `outreach_log.jsonl`. A buyer can audit any row.
- **No silent failures.** A provider with no email is not dropped: the report
  shows the route (form/phone) and, for phone-only, a call sheet with the three
  questions and slots to record the answer.
- **Throttled and idempotent.** Sends are spaced, logged, and a re-run skips
  addresses already in the log (see `send.py` log check in `cli.py send`).

## Usage

```bash
pip install requests
python cli.py demo --lat 39.7392 --lon -104.9903 --radius 12000 \
  --event "Team dinner" --date 2026-11-14 --headcount 24 \
  --budget "60-80" --dietary "2 vegan, 1 gluten-free"
```

Outputs `venues.json`, `enquiries.json`, `brief.json` and `reports/quotes-*.md|csv`.

Send (dry-run first, then live):

```bash
python cli.py send --brief brief.json --venues venues.json --limit 10
RESEND_API_KEY=... python cli.py send --brief brief.json --venues venues.json --limit 10 --live
```

Collect replies:

```bash
python cli.py parse --host imap.example.com --user me@example.com \
  --password "$IMAP_PASS" --venues venues.json --days 7
```

## Sample output (real run, Denver, 2026-10-20)

93 providers discovered for group-dining tags in a 12 km radius; 40 of the
first 40 sampled carried a usable email in OSM tags. The generated report lists
every provider with its route, and fills price/availability only from replies.

## Limits, stated plainly

- Coverage depends on OSM tagging quality; in dense US metros it is good, in
  places where businesses are unmapped it drops. The enrichment step recovers
  some of that from websites, not all.
- Reply parsing is regex-based. It handles the common shapes ("$65 per person,
  $500 minimum, 48h notice") and flags everything else as unparsed rather than
  guessing; the raw excerpt is kept for a human second pass.
- It does not place phone calls. Phone-only providers get a call sheet.
