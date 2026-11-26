"""Holt stündlich die Versandmails, wertet sie aus und meldet neue "kommt heute"- und Abhol-Pakete per Event."""
from datetime import timedelta
import imaplib
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .mailbox import fetch
from .parcels import ABHOLEN, ABHOLFRIST_TAGE, HEUTE, SENDERS, ZUGESTELLT, classify, summarize

_LOGGER = logging.getLogger(__name__)
DOMAIN = "pakete"
EVENT_HEUTE = f"{DOMAIN}_kommt_heute"
EVENT_ABHOLEN = f"{DOMAIN}_abholen"
EVENT_ZUGESTELLT = f"{DOMAIN}_zugestellt"
DAYS_BACK = ABHOLFRIST_TAGE  # Abholmeldungen gelten eine Woche, unterwegs filtert parcels selbst


class PaketeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, conf: dict):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=1))
        self.conf = conf
        self.store = Store(hass, 1, DOMAIN)
        self.notified: set[str] | None = None  # None = erster Lauf, Bestand nicht melden
        self.picked_up_until = None  # Knopf "abgeholt": ältere Abholmeldungen ausblenden
        self._loaded = False

    async def _async_update_data(self):
        if not self._loaded:
            stored = await self.store.async_load() or {}
            self.notified = set(stored["notified"]) if "notified" in stored else None
            if stored.get("picked_up_until"):
                self.picked_up_until = dt_util.parse_datetime(stored["picked_up_until"])
            self._loaded = True
        today = dt_util.now().date()
        c = self.conf
        try:
            raw = await self.hass.async_add_executor_job(
                fetch, c["host"], c["port"], c["username"], c["password"], c["folders"],
                today - timedelta(days=DAYS_BACK), SENDERS,
            )
        except imaplib.IMAP4.error as err:
            raise ConfigEntryAuthFailed(err) from err
        except OSError as err:
            raise UpdateFailed(err) from err

        mails = []
        for m in raw:
            hit = classify(m["from"], m["subject"])
            if hit:
                carrier, status, info, key = hit
                mails.append({"id": m["id"], "carrier": carrier, "status": status, "info": info, "key": key,
                              "date": dt_util.as_local(m["date"])})
        result = summarize(mails, today, self.picked_up_until)
        _LOGGER.debug("%s Mails, %s erkannt: %s", len(raw), len(mails), [(m["carrier"], m["status"], m["info"], str(m["date"])) for m in mails])
        for m in raw:
            if not classify(m["from"], m["subject"]):
                _LOGGER.debug("nicht erkannt: %s | %s", m["from"], m["subject"])

        data = {k: [{"dienst": m["carrier"], "info": m["info"]} for m in v] for k, v in result.items()}
        if self.notified is not None and not self.hass.is_running:
            # HA startet noch, Automationen hören evtl. nicht zu: nichts melden und nichts merken,
            # der nächste Abruf (1 h) holt das nach.
            return data
        shown = {m["id"] for m in result[HEUTE] + result[ABHOLEN] + result[ZUGESTELLT]}
        if self.notified is not None:
            for event, status in ((EVENT_HEUTE, HEUTE), (EVENT_ABHOLEN, ABHOLEN), (EVENT_ZUGESTELLT, ZUGESTELLT)):
                for m in result[status]:
                    if m["id"] not in self.notified:
                        self.hass.bus.async_fire(event, {"dienst": m["carrier"], "info": m["info"]})
        # Nur IDs der letzten Tage merken, sonst wächst der Speicher endlos
        recent = {m["id"] for m in mails}
        new_notified = ((self.notified or set()) & recent) | shown
        if new_notified != self.notified:
            self.notified = new_notified
            await self._save()
        return data

    async def _save(self):
        await self.store.async_save({
            "notified": sorted(self.notified or []),
            "picked_up_until": self.picked_up_until.isoformat() if self.picked_up_until else None,
        })

    async def mark_picked_up(self):
        """Alle bisherigen Abholmeldungen als abgeholt markieren (neue Erinnerungen zeigen es wieder)."""
        self.picked_up_until = dt_util.now()
        await self._save()
        await self.async_request_refresh()
