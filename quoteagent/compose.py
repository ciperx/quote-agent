"""Compose the outbound enquiry: exactly three closed questions."""
from textwrap import dedent

SUBJECT = "Group dining enquiry — {date} for {headcount} guests"


def brief_line(brief):
    bits = [f"{brief['headcount']} guests", brief["date"]]
    if brief.get("budget_per_head"):
        bits.append(f"budget ~{brief['budget_per_head']} per head")
    if brief.get("dietary"):
        bits.append(brief["dietary"])
    return ", ".join(bits)


def compose(venue, brief, sender_name="Quote Agent", reply_to=None):
    subj = SUBJECT.format(date=brief["date"], headcount=brief["headcount"])
    body = dedent(f"""\
    Hello {venue['name']} team,

    I am sourcing a group dining booking and would like to check one thing with you before shortlisting.

    Brief: {brief_line(brief)}.
    {("Room or privacy needs: " + brief["privacy"] + ".") if brief.get("privacy") else ""}

    Three questions, answer in one line each if that is easiest:
    1. Are you available on {brief['date']} for {brief['headcount']} guests?
    2. What is the price per head for that group, and is there a minimum spend or deposit?
    3. Can you handle {brief.get('dietary') or 'the dietary needs above'} — and which menu tier suits a group?

    If a group menu or PDF exists, a link is enough; I will read it.

    Thanks,
    {sender_name}
    {reply_to or ""}
    """).replace("\n    ", "\n").strip()
    return {"to": venue.get("email"), "subject": subj, "text": body,
            "venue": venue["name"], "route": "email" if venue.get("email") else "phone"}


def phone_script(venue, brief):
    return dedent(f"""\
    CALL SCRIPT — {venue['name']} — {venue.get('phone') or 'no number on record'}
    Hi, I'd like to check availability for {brief_line(brief)}.
    1. Free on {brief['date']}?
    2. Price per head, minimum spend, deposit?
    3. Dietary: {brief.get('dietary') or 'standard'}?
    Record: yes/no, price, deposit, who you spoke to, time.
    """).strip()
