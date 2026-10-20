"""Enrich a provider record with a reachable contact route.

Given a website, look for a mailto: address on the homepage and on common
contact pages. No login, no headless browser: plain HTTP + regex, with a
per-host politeness delay. Anything found is recorded with the URL it came
from so the report can show provenance.
"""
import re
import time
import urllib.parse

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; quote-agent/0.9; +https://ggez.my.id)"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
BAD = ("example.com", "sentry", "wixpress", "domain.com", "@2x", ".png", ".jpg", "godaddy")
CONTACT_PATHS = ("", "/contact", "/contact-us", "/about", "/catering", "/private-dining", "/events")


def _emails_on(url, timeout=15):
    try:
        r = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
    except Exception:
        return [], None
    if r.status_code >= 400 or "text/html" not in r.headers.get("content-type", ""):
        return [], None
    html = r.text[:400000]
    found = []
    for m in EMAIL_RE.findall(html):
        low = m.lower()
        if any(b in low for b in BAD):
            continue
        if low not in found:
            found.append(low)
    return found, (r.url if found else None)


def enrich(venue, max_paths=len(CONTACT_PATHS)):
    """Mutates a copy of venue with email/email_source/form_url."""
    v = dict(venue)
    if v.get("email"):
        v["email_source"] = "osm"
        return v
    site = v.get("website")
    if not site:
        return v
    if not site.startswith("http"):
        site = "https://" + site
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))
    for path in CONTACT_PATHS[:max_paths]:
        url = base + path if path else site
        emails, final = _emails_on(url)
        if emails:
            v["email"] = emails[0]
            v["email_source"] = final or url
            break
        time.sleep(0.4)
    return v


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(enrich(json.loads(sys.argv[1])), indent=1))
