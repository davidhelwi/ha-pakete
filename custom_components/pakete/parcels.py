"""Paketstatus aus den Betreffzeilen deutscher Versandmails. Ohne HA-Abhängigkeit (testbar).

Regeln aus echten Versandmails (Stand 2026-10-14). Reihenfolge je Dienst zählt:
"wird gleich zugestellt" ist heute, nicht zugestellt. IGNORIEREN zuerst (Werbung, eigene Einlieferung).
"""
import re

HEUTE, UNTERWEGS, ZUGESTELLT, ABHOLEN, IGNORIEREN = "heute", "unterwegs", "zugestellt", "abholen", None
ABHOLFRIST_TAGE = 7  # DHL/DPD schicken nach etwa 7 Tagen zurück
UNTERWEGS_TAGE = 3

RULES = {
    "Amazon": (
        "amazon.de",
        [(HEUTE, r"^in zustellung"), (ZUGESTELLT, r"^(geliefert|zugestellt)"), (UNTERWEGS, r"^vers(endet|andt)")],
    ),
    "DHL": (
        "dhl.de",
        [
            (IGNORIEREN, r"einlieferungsbeleg|noch platz|anliegen zum thema"),
            (ABHOLEN, r"packstation|abholbereit|zur abholung"),
            (HEUTE, r"kommt heute|wird gleich zugestellt"),
            (ZUGESTELLT, r"zugestellt|ablageort"),
            (UNTERWEGS, r"unterwegs|auf dem weg"),
        ],
    ),
    "DPD": (
        "dpd.de",
        [
            (ABHOLEN, r"paketabholung"),
            (HEUTE, r"uhr kommt ihr dpd paket"),
            (ZUGESTELLT, r"abstellung|ihr paket ist da"),
            (UNTERWEGS, r"bald ist ihr dpd paket da|auf dem weg|erhält in kürze"),
        ],
    ),
    "Hermes": (
        "myhermes.de",
        [(HEUTE, r"kommt heute"), (ZUGESTELLT, r"erfolgreiche|zugestellt"), (UNTERWEGS, r"auf dem weg|zustellversuch")],
    ),
}
SENDERS = [sender for sender, _ in RULES.values()]


def classify(sender: str, subject: str):
    """(Dienst, Status, Info, Schlüssel) oder None, wenn die Mail keine Sendungsmeldung ist.

    Info ist der Anzeigetext, Schlüssel (Artikel/Shop) ordnet Mails derselben Sendung zu.
    """
    sender, low = sender.lower(), subject.lower()
    for carrier, (domain, rules) in RULES.items():
        if domain not in sender:
            continue
        for status, pattern in rules:
            if re.search(pattern, low):
                if status is IGNORIEREN:
                    return None
                k = key(carrier, subject)
                return carrier, status, info(carrier, status, subject) or k, k
    return None


def key(carrier: str, subject: str) -> str:
    """Artikel (Amazon) bzw. Shop (DHL), steht in jeder Mail derselben Sendung."""
    if carrier == "Amazon" and ":" in subject:
        return re.sub(r'[„“"]', "", subject.split(":", 1)[1]).replace("...", "…").strip()
    m = re.search(r"Ihre (.+?) Sendung", subject) if carrier == "DHL" else None
    return m.group(1) if m else ""


def info(carrier: str, status: str, subject: str) -> str:
    """Zusatz für Push und Bon: Abholort, DPD-Zeitfenster oder Hermes-Shop ("" = Schlüssel nehmen)."""
    if status == ABHOLEN:
        place = re.search(r"(Packstation(?: \d+)?|Filiale|Paketshop)", subject, re.I)
        shop = key(carrier, subject)
        return (place.group(1) if place else "Abholung") + (f" ({shop})" if shop else "")
    if status == ZUGESTELLT:
        where = re.search(r"(ablageort|briefkasten|nachbar|haustür|abstellung)", subject, re.I)
        text = {"ablageort": "am Ablageort", "briefkasten": "im Briefkasten", "nachbar": "beim Nachbarn",
                "haustür": "an der Haustür", "abstellung": "abgestellt"}.get(where.group(1).lower(), "") if where else ""
        shop = key(carrier, subject)
        return ", ".join(x for x in (text, shop) if x)
    pattern = {"DPD": r"((?:Zwischen|Nach|Vor|Ab) [\d:]+(?: und [\d:]+)? Uhr)", "Hermes": r"von (.+?) ist auf dem Weg"}.get(carrier)
    m = re.search(pattern, subject) if pattern else None
    return m.group(1) if m else ""


def summarize(mails, today, picked_up_until=None):
    """mails: [{carrier, status, info, key, date (lokal, aware), id}] der letzten Tage.

    Amazon und DHL tragen Artikel bzw. Shop in jedem Betreff: Zuordnung über diesen Text.
    DPD/Hermes haben keine gemeinsame Kennung: Zählung je Dienst, die ältesten offenen
    Meldungen gelten als erledigt. Eine Sendung schickt meist "heute" UND "zugestellt",
    daher zählt max() statt Summe. "abholen" gilt wie zugestellt als Endstatus und bleibt
    sichtbar, bis "abgeholt" gedrückt wurde (picked_up_until) oder die Abholfrist um ist.
    """
    out = {HEUTE: [], UNTERWEGS: [], ABHOLEN: [], ZUGESTELLT: []}
    for carrier in RULES:
        own = sorted((m for m in mails if m["carrier"] == carrier), key=lambda m: m["date"])
        by = {s: [m for m in own if m["status"] == s] for s in (HEUTE, UNTERWEGS, ZUGESTELLT, ABHOLEN)}
        end = by[ZUGESTELLT] + by[ABHOLEN]
        recent_unterwegs = [m for m in by[UNTERWEGS] if (today - m["date"].date()).days <= UNTERWEGS_TAGE]
        heute_today = [m for m in by[HEUTE] if m["date"].date() == today]
        done_today = [m for m in end if m["date"].date() == today]
        out[ZUGESTELLT] += [m for m in by[ZUGESTELLT] if m["date"].date() == today]
        if carrier in ("Amazon", "DHL"):
            done = {m["key"] for m in done_today}
            later = {m["key"] for m in by[HEUTE] + end}
            out[HEUTE] += [m for m in heute_today if m["key"] not in done]
            out[UNTERWEGS] += [m for m in recent_unterwegs if m["key"] not in later]
        else:
            out[HEUTE] += heute_today[len(done_today):]
            out[UNTERWEGS] += recent_unterwegs[max(len(by[HEUTE]), len(end)):]
        # Erinnerungen ("liegt seit 2 Tagen ...") zur selben Sendung nur einmal zeigen
        waiting = {}
        for m in by[ABHOLEN]:
            if (today - m["date"].date()).days < ABHOLFRIST_TAGE and (picked_up_until is None or m["date"] > picked_up_until):
                waiting.setdefault(m["info"], m)
        out[ABHOLEN] += waiting.values()
    return out
