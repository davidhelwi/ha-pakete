"""Selbsttest mit echten (anonymisierten) Betreffzeilen: python3 tests/test_parcels.py"""
from datetime import datetime, timedelta, timezone
import importlib.util
import pathlib

path = pathlib.Path(__file__).parent.parent / "custom_components/pakete/parcels.py"
spec = importlib.util.spec_from_file_location("parcels", path)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

CASES = [
    ("Amazon.de <shipment-tracking@amazon.de>", "In Zustellung: „Edelstahl Topfset...“", ("Amazon", "heute", "Edelstahl Topfset…")),
    ("Amazon.de <versandbestaetigung@amazon.de>", "Versendet: „Edelstahl Topfset...“", ("Amazon", "unterwegs", "Edelstahl Topfset…")),
    ("Amazon.de <versandbestaetigung@amazon.de>", "Versandt: „Faltbarer Wäschekorb...“ und 1 weiterer Artikel", ("Amazon", "unterwegs", None)),
    ("Amazon.de <order-update@amazon.de>", 'Geliefert: "Fahrradlampe,...“', ("Amazon", "zugestellt", None)),
    ("Amazon.de <bestellbestaetigung@amazon.de>", "Bestellt: „Edelstahl Topfset...“", None),
    ("DHL Live Tracking <livetracking@dhl.de>", "Ihre Musterversand GmbH Sendung kommt heute - Jetzt Live verfolgen...", ("DHL", "heute", "Musterversand GmbH")),
    ("DHL Paket <noreply@dhl.de>", "Ihre Kaffee & Co Sendung wird gleich zugestellt", ("DHL", "heute", "Kaffee & Co")),
    ("DHL Paketankündigung <paketankuendigung@dhl.de>", "Ihre Buchladen Beispiel Sendung ist unterwegs", ("DHL", "unterwegs", "Buchladen Beispiel")),
    ("DHL Zustellung <zustellung@dhl.de>", "Ihre Beispiel GmbH Sendung wurde im Briefkasten zugestellt", ("DHL", "zugestellt", "im Briefkasten, Beispiel GmbH")),
    ("DHL Abholinformation <abholung@dhl.de>", "Ihre Musterversand GmbH Sendung ist in der Filiale abholbereit", ("DHL", "abholen", "Filiale (Musterversand GmbH)")),
    ("DHL Paket <noreply@dhl.de>", "Ihre Sendung liegt in der Packstation 123", ("DHL", "abholen", "Packstation 123")),
    ("DHL Paket <noreply@dhl.de>", "🌍 Ihre Sendung liegt seit 2 Tagen in der Packstation 123", ("DHL", "abholen", "Packstation 123")),
    ("DHL Paket <noreply@dhl.de>", "Ihre Amazon Sendung liegt in der Packstation", ("DHL", "abholen", "Packstation (Amazon)")),
    ("DHL Paket <noreply@dhl.de>", "Ihre Germany Sorting Center Sendung liegt zur Abholung in der Filiale bereit", ("DHL", "abholen", "Filiale (Germany Sorting Center)")),
    ("❗ DHL Zustell-Update <zustellung@dhl.de>", "Ihre Musterversand GmbH Sendung ist auf dem Weg in eine Filiale", ("DHL", "unterwegs", "Musterversand GmbH")),
    ("DHL Paket <paket@dhl.de>", "Die Packstation 456, Musterstr. hat auch noch Platz für Ihre Sendungen", None),
    ("DHL Paket <noreply@dhl.de>", "Einlieferungsbeleg: Ihr Versand an der Packstation", None),
    ("DPD <noreply@service.dpd.de>", "Ihr Code für die Paketabholung im DPD Pickup Paketshop", ("DPD", "abholen", "Paketshop")),
    ("DPD <noreply@service.dpd.de>", "Der Pickup Paketshop erhält in Kürze Ihr DPD Paket", ("DPD", "unterwegs", None)),
    ("DPD <noreply@service.dpd.de>", "Zwischen 10:15 und 12:15 Uhr kommt Ihr DPD Paket", ("DPD", "heute", "Zwischen 10:15 und 12:15 Uhr")),
    ("DPD <noreply@service.dpd.de>", "Nach 18:12 Uhr kommt Ihr DPD Paket", ("DPD", "heute", "Nach 18:12 Uhr")),
    ("DPD <noreply@service.dpd.de>", "Bald ist Ihr DPD Paket da", ("DPD", "unterwegs", None)),
    ("DPD <noreply@service.dpd.de>", "Die Abstellung Ihres DPD Pakets ist erfolgt", ("DPD", "zugestellt", None)),
    ("Hermes <noreply@paketankuendigung.myhermes.de>", "Deine Sendung kommt heute.", ("Hermes", "heute", None)),
    ("Hermes <noreply@paketankuendigung.myhermes.de>", "Deine Hermes Sendung von AliExpress ist auf dem Weg", ("Hermes", "unterwegs", "AliExpress")),
    ("Hermes <noreply@paketankuendigung.myhermes.de>", "Erfolgreiche Haustürzustellung", ("Hermes", "zugestellt", None)),
]
for sender, subject, want in CASES:
    got = p.classify(sender, subject)
    if want is None:
        assert got is None, (subject, got)
    else:
        assert got[:2] == want[:2], (subject, got)
        if want[2] is not None:
            assert got[2] == want[2], (subject, got)
print("ok klassifizierung")

TZ = timezone(timedelta(hours=2))
TODAY = datetime(2026, 10, 14, tzinfo=TZ)


def m(carrier, status, info, days_ago, hour, id_):
    return {"carrier": carrier, "status": status, "info": info, "key": info if carrier in ("Amazon", "DHL") else "", "id": id_,
            "date": TODAY - timedelta(days=days_ago) + timedelta(hours=hour)}


mails = [
    # Amazon: Topfset gestern versendet, heute in Zustellung -> heute
    m("Amazon", "unterwegs", "Topfset", 1, 23, "a1"), m("Amazon", "heute", "Topfset", 0, 11, "a2"),
    # Amazon: Heckklappe gestern komplett geliefert -> weder heute noch unterwegs
    m("Amazon", "unterwegs", "Heck", 2, 22, "a3"), m("Amazon", "heute", "Heck", 1, 12, "a4"), m("Amazon", "zugestellt", "Heck", 1, 18, "a5"),
    # Amazon: Wäschekorb nur versendet -> unterwegs
    m("Amazon", "unterwegs", "Korb", 0, 6, "a6"),
    # DPD: Paket 1 gestern komplett, Paket 2 heute angekündigt, Paket 3 nur "bald da"
    m("DPD", "unterwegs", "", 2, 16, "d1"), m("DPD", "heute", "Zwischen 9 und 11", 1, 6, "d2"), m("DPD", "zugestellt", "", 1, 10, "d3"),
    m("DPD", "unterwegs", "", 1, 18, "d4"), m("DPD", "heute", "Zwischen 10 und 12", 0, 6, "d5"),
    m("DPD", "unterwegs", "", 0, 15, "d6"),
    # Hermes: heute angekündigt und schon zugestellt -> nichts offen
    m("Hermes", "unterwegs", "AliExpress", 1, 17, "h1"), m("Hermes", "heute", "", 0, 9, "h2"), m("Hermes", "zugestellt", "", 0, 14, "h3"),
]
res = p.summarize(mails, TODAY.date())
assert sorted(x["id"] for x in res["heute"]) == ["a2", "d5"], res["heute"]
assert sorted(x["id"] for x in res["unterwegs"]) == ["a6", "d6"], res["unterwegs"]
print("ok zusammenfassung")

# Abholen: DHL Packstation vor 2 Tagen + Erinnerung heute -> einmal; Musterversand-Filiale vor 9 Tagen -> verfallen
ab = [
    m("DHL", "unterwegs", "Amazon", 3, 10, "x1"),
    m("DHL", "abholen", "Packstation 123 (Amazon)", 2, 14, "x2"), m("DHL", "abholen", "Packstation 123 (Amazon)", 0, 14, "x3"),
    m("DHL", "abholen", "Filiale (Musterversand)", 9, 10, "x4"),
]
for x in ab[1:]:
    x["key"] = "Amazon" if "Amazon" in x["info"] else "Musterversand"
r = p.summarize(ab, TODAY.date())
assert [x["id"] for x in r["abholen"]] == ["x2"] and r["unterwegs"] == [], r
# Knopf "abgeholt" gestern: alte Meldung weg, heutige Erinnerung zeigt sie wieder
r = p.summarize(ab, TODAY.date(), picked_up_until=TODAY - timedelta(hours=12))
assert [x["id"] for x in r["abholen"]] == ["x3"], r
r = p.summarize(ab, TODAY.date(), picked_up_until=TODAY + timedelta(hours=20))
assert r["abholen"] == [], r
print("ok abholen")

for sender, subject, want in [
    ("DHL Paket <noreply@dhl.de>", "Ihre Kaffee & Co Sendung liegt am gewünschten Ablageort", "am Ablageort, Kaffee & Co"),
    ("DHL Zustellung <zustellung@dhl.de>", "Ihre Beispiel GmbH Sendung wurde im Briefkasten zugestellt", "im Briefkasten, Beispiel GmbH"),
    ("DPD <noreply@service.dpd.de>", "Die Abstellung Ihres DPD Pakets ist erfolgt", "abgestellt"),
    ("Hermes <noreply@paketankuendigung.myhermes.de>", "Erfolgreiche Haustürzustellung", "an der Haustür"),
    ("Amazon.de <order-update@amazon.de>", 'Geliefert: "Edelstahl Topfset...“', "Edelstahl Topfset…"),
]:
    got = p.classify(sender, subject)
    assert got[1] == "zugestellt" and got[2] == want, (subject, got)
r = p.summarize(mails, TODAY.date())
assert [x["id"] for x in r["zugestellt"]] == ["h3"], r["zugestellt"]
print("ok zugestellt")
