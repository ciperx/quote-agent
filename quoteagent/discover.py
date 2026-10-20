"""Provider discovery via OpenStreetMap Overpass (no API key, no login)."""
import json
import urllib.parse

import requests

OVERPASS = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "quote-agent/0.9 (local-services sourcing; contact ops@ggez.my.id)"}

# Tags that actually carry local service / catering / group-dining businesses.
QUERY_TAGS = [
    '["amenity"="caterer"]',
    '["shop"="caterer"]',
    '["office"="catering"]',
    '["catering"="yes"]',
    '["amenity"="restaurant"]["website"]["capacity"]',
    '["amenity"="restaurant"]["contact:website"]',
    '["amenity"="restaurant"]["email"]',
]


def _q(tags, lat, lon, radius_m, limit):
    parts = []
    for t in tags:
        parts.append(f'node{t}(around:{radius_m},{lat},{lon});')
        parts.append(f'way{t}(around:{radius_m},{lat},{lon});')
    return f"[out:json][timeout:60];({''.join(parts)});out center {limit};"


def discover(lat, lon, radius_m=8000, limit=120, timeout=90):
    """Return deduped provider records in a normalised shape."""
    query = _q(QUERY_TAGS, lat, lon, radius_m, limit)
    last = None
    for endpoint in (OVERPASS, "https://overpass.kumi.systems/api/interpreter"):
        try:
            r = requests.get(endpoint, params={"data": query},
                             headers={**UA, "Accept": "application/json"}, timeout=timeout)
            r.raise_for_status()
        except Exception as exc:  # endpoint down / 502 / 429 -> try the next mirror
            last = exc
            continue
        seen, out = set(), []
        for el in r.json().get("elements", []):
            tags = el.get("tags", {}) or {}
            name = tags.get("name")
            if not name:
                continue
            key = name.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            email = tags.get("email") or tags.get("contact:email")
            phone = tags.get("phone") or tags.get("contact:phone")
            site = tags.get("website") or tags.get("contact:website")
            center = el.get("center") or {}
            out.append({
                "name": name,
                "kind": tags.get("amenity") or tags.get("shop") or tags.get("office") or "unknown",
                "email": email,
                "phone": phone,
                "website": site,
                "street": " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")])),
                "city": tags.get("addr:city"),
                "cuisine": tags.get("cuisine"),
                "capacity": tags.get("capacity"),
                "lat": el.get("lat") or center.get("lat"),
                "lon": el.get("lon") or center.get("lon"),
                "osm": f"{el.get('type')}/{el.get('id')}",
                "contact_route": "email" if email else ("form" if site else ("phone" if phone else "unknown")),
            })
        out.sort(key=lambda v: (v["contact_route"] != "email", v["name"].lower()))
        return out
    raise RuntimeError(f"all Overpass mirrors failed: {last}")


def overpass_url(query_parts="caterer"):
    return "https://overpass-turbo.eu/?Q=" + urllib.parse.quote(query_parts)


if __name__ == "__main__":
    import sys
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    print(json.dumps(discover(lat, lon), indent=1)[:2000])
