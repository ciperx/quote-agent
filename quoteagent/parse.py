"""Parse replies into structured quotes.

Read-only IMAP against a mailbox the operator supplies. Each reply is matched
to a venue by sender address, then scanned for the three answers the enquiry
asked for. Nothing is inferred: a field that is not present stays null and the
report shows it as "not stated", never as a guess.
"""
import email
import imaplib
import re
from email.header import decode_header

MONEY = re.compile(r"(?:[$£€]\s?|\b(?:usd|eur|gbp)\s?)(\d{1,4}(?:[.,]\d{1,2})?)", re.I)
PER_HEAD = re.compile(r"(per\s+(?:head|person|guest|pp)|\bpp\b|/\s*(?:head|person|guest))", re.I)
DEPOSIT = re.compile(r"(deposit|minimum spend|min\.? spend)[^.\n]{0,60}?", re.I)
NO_RE = re.compile(r"\b(not available|fully booked|no availability|unavailable|booked out)\b", re.I)
YES_RE = re.compile(r"\b(available|we can|yes,|we have space|open on)\b", re.I)
DIET = re.compile(r"\b(vegetarian|vegan|gluten[- ]free|halal|kosher|nut[- ]free|dairy[- ]free)\b", re.I)


def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def _decode(v):
    if not v:
        return ""
    out = []
    for part, enc in decode_header(v):
        out.append(part.decode(enc or "utf-8", "replace") if isinstance(part, bytes) else part)
    return _clean(" ".join(out))


def parse_body(raw):
    msg = email.message_from_bytes(raw) if isinstance(raw, bytes) else email.message_from_string(raw)
    text = ""
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain":
                try:
                    text += p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "replace")
                except Exception:
                    pass
    else:
        try:
            text = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")
        except Exception:
            text = str(msg.get_payload())
    return {"from": _decode(msg.get("From")), "subject": _decode(msg.get("Subject")),
            "date": _clean(msg.get("Date")), "text": _clean(text)}


def extract_quote(text):
    # Drop interrogative sentences first: our own enquiry asks "Are you
    # available on ...?" and must never be read as a yes from the vendor.
    statements = " ".join(s for s in re.split(r"(?<=[.!?])\s+", text) if not s.strip().endswith("?"))
    prices = MONEY.findall(statements)
    price = None
    for p in prices:
        price = float(p.replace(",", ""))
        break
    m = DEPOSIT.search(statements)
    return {
        "available": ("no" if NO_RE.search(statements) else ("yes" if YES_RE.search(statements) else None)),
        "price": price,
        "per_head": bool(PER_HEAD.search(statements)),
        "deposit_note": _clean(m.group(0))[:90] if m else None,
        "dietary": sorted({d.lower() for d in DIET.findall(statements)}) or None,
        "raw_excerpt": text[:280],
    }


def fetch(host, user, password, since_days=7, mailbox="INBOX", limit=60):
    out = []
    m = imaplib.IMAP4_SSL(host)
    m.login(user, password)
    m.select(mailbox, readonly=True)
    typ, data = m.search(None, f'(SINCE {_imap_date(since_days)})')
    ids = (data[0].split() if data and data[0] else [])[-limit:]
    for i in ids:
        typ, msg_data = m.fetch(i, "(RFC822)")
        if typ != "OK":
            continue
        for part in msg_data:
            if isinstance(part, tuple):
                out.append(parse_body(part[1]))
    m.logout()
    return out


def _imap_date(days):
    import datetime as dt
    d = dt.date.today() - dt.timedelta(days=days)
    return d.strftime("%d-%b-%Y")


def match_to_venues(replies, venues):
    by_email = {(v.get("email") or "").lower(): v for v in venues if v.get("email")}
    rows = []
    for r in replies:
        addr = re.search(r"[\w.+-]+@[\w.-]+", r["from"])
        addr = addr.group(0).lower() if addr else ""
        v = by_email.get(addr)
        if not v:
            continue
        q = extract_quote(r["text"])
        q.update({"venue": v["name"], "email": addr, "subject": r["subject"]})
        rows.append(q)
    return rows
