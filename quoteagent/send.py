"""Send enquiries through Resend (domain ggez.my.id is verified) or SMTP.

Dry-run by default: nothing leaves the machine until --send is passed.
Every send is logged with provider message id so a quote can be traced back
to the exact message that produced it.
"""
import json
import os
import time

import requests

RESEND = "https://api.resend.com/emails"
LOG = "outreach_log.jsonl"


def _key():
    if os.environ.get("RESEND_API_KEY"):
        return os.environ["RESEND_API_KEY"]
    path = os.path.join(os.path.dirname(__file__), "..", "secrets", "resend.env")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("RESEND_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def send(msg, sender="quotes@ggez.my.id", sender_name="Quote Agent",
         reply_to="quotes@ggez.my.id", dry_run=True, throttle=3.0):
    if not msg.get("to"):
        return {"ok": False, "reason": "no recipient"}
    if dry_run:
        rec = {"ok": True, "dry_run": True, "to": msg["to"], "subject": msg["subject"]}
        _log(rec)
        return rec
    key = _key()
    if not key:
        return {"ok": False, "reason": "no RESEND_API_KEY"}
    payload = {
        "from": f"{sender_name} <{sender}>",
        "to": [msg["to"]],
        "reply_to": reply_to,
        "subject": msg["subject"],
        "text": msg["text"],
    }
    r = requests.post(RESEND, json=payload, timeout=40,
                      headers={"authorization": "Bearer " + key,
                               "content-type": "application/json"})
    rec = {"ok": r.status_code in (200, 201), "status": r.status_code,
           "to": msg["to"], "subject": msg["subject"], "body": r.text[:300]}
    _log(rec)
    time.sleep(throttle)
    return rec


def _log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
