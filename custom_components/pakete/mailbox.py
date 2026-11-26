"""IMAP-Abruf nur der Kopfzeilen, ohne Mails als gelesen zu markieren. Blockierend: im Executor aufrufen."""
from datetime import date
import email
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
import imaplib
import logging

_LOGGER = logging.getLogger(__name__)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _text(value: str) -> str:
    # Umbrochene Kopfzeilen ("Musterversand\r\n Sendung") zu einer Zeile, sonst greifen die Regeln nicht
    return " ".join(str(make_header(decode_header(value or ""))).split())


def fetch(host, port, username, password, folders, since: date, senders):
    since_s = f"{since.day:02d}-{MONTHS[since.month - 1]}-{since.year}"  # IMAP will englische Monate
    seen, out = set(), []
    with imaplib.IMAP4_SSL(host, port, timeout=30) as imap:
        imap.login(username, password)
        for folder in folders:
            status = imap.select(f'"{folder}"', readonly=True)
            if status[0] != "OK":
                _LOGGER.warning("Ordner %r nicht lesbar: %s", folder, status)
                continue
            for sender in senders:
                ok, data = imap.search(None, "SINCE", since_s, "FROM", f'"{sender}"')
                ids = data[0].split() if ok == "OK" and data and data[0] else []
                _LOGGER.debug("%s / %s: %s Treffer (%s)", folder, sender, len(ids), ok)
                if not ids:
                    continue
                ok, parts = imap.fetch(b",".join(ids), "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])")
                for part in parts if ok == "OK" else []:
                    if not isinstance(part, tuple):
                        continue
                    msg = email.message_from_bytes(part[1])
                    try:
                        sent = parsedate_to_datetime(msg["Date"])
                    except (TypeError, ValueError):
                        continue
                    mid = msg.get("Message-ID") or f"{folder}|{msg.get('Date')}|{msg.get('Subject')}"
                    if mid in seen:
                        continue
                    seen.add(mid)
                    out.append({"id": mid, "from": _text(msg.get("From")), "subject": _text(msg.get("Subject")), "date": sent})
    return out
