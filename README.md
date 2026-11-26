# Pakete für Home Assistant

Liest die Versandmails von **Amazon, DHL, DPD und Hermes** per IMAP und zeigt in Home Assistant, welche Pakete **heute** kommen, welche **unterwegs** sind, welche in Packstation, Filiale oder Paketshop **zum Abholen** liegen und welche heute **zugestellt** wurden.

- Nur die Kopfzeilen werden gelesen (Absender, Betreff, Datum). Mails werden nicht als gelesen markiert, nichts wird verschoben oder gelöscht.
- Keine Cloud, kein Tracking-Dienst, kein Konto bei den Versanddiensten nötig.
- Ausgelegt auf **deutsche** Versandmails (Betreffzeilen wie „In Zustellung:“, „Ihre … Sendung kommt heute“).

## Installation

### Über HACS

1. HACS → Integrationen → Menü oben rechts → **Benutzerdefinierte Repositories**.
2. `https://github.com/davidhelwi/ha-pakete` als Typ **Integration** hinzufügen.
3. „Pakete“ installieren und Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/pakete` nach `config/custom_components/pakete` kopieren und Home Assistant neu starten.

## Einrichtung

Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Pakete“.

| Feld | Bedeutung |
|---|---|
| IMAP-Server, Port | z. B. `imap.gmx.net`, `993` (nur SSL) |
| Benutzername, Passwort | Zugang zum Postfach. Bei Gmail, iCloud, Outlook und anderen mit Zwei-Faktor ein **App-Passwort** verwenden |
| Ordner | kommagetrennt, z. B. `INBOX, Shopping`. Nur nötig, wenn Versandmails per Filter in Unterordner sortiert werden |

Abgefragt wird **stündlich**, ausgewertet werden die Mails der letzten 7 Tage.

## Entitäten

| Entität | Inhalt |
|---|---|
| `sensor.pakete_heute` | Anzahl der Pakete, die heute kommen |
| `sensor.pakete_unterwegs` | verschickt, aber noch nicht angekündigt oder zugestellt (letzte 3 Tage) |
| `sensor.pakete_abholen` | liegt in Packstation, Filiale oder Paketshop (höchstens 7 Tage) |
| `sensor.pakete_zugestellt` | heute zugestellt, mit Ablageort wenn bekannt |
| `button.pakete_abgeholt` | blendet alle aktuellen Abholmeldungen aus. Kommt danach eine Erinnerung von DHL („liegt seit 2 Tagen …“), erscheint das Paket wieder |

Jeder Sensor hat das Attribut `pakete`, eine Liste mit `dienst` und `info`, zum Beispiel:

```yaml
pakete:
  - dienst: DHL
    info: Packstation 123 (Amazon)
  - dienst: DPD
    info: Zwischen 10:15 und 12:15 Uhr
```

`info` ist je nach Dienst der Artikel (Amazon), der Shop (DHL, Hermes), das Zeitfenster (DPD), der Abholort oder der Ablageort.

## Events

Für jedes neu erkannte Paket feuert die Integration ein Event mit `dienst` und `info`:

| Event | Wann |
|---|---|
| `pakete_kommt_heute` | Paket kommt heute |
| `pakete_abholen` | Paket liegt zur Abholung bereit |
| `pakete_zugestellt` | Paket wurde zugestellt |

Beim ersten Abruf nach der Einrichtung werden vorhandene Pakete nur gemerkt, nicht gemeldet.

### Beispiel: Push aufs Handy

```yaml
alias: "Pakete: Push"
triggers:
  - trigger: event
    event_type: pakete_kommt_heute
    id: heute
  - trigger: event
    event_type: pakete_abholen
    id: abholen
  - trigger: event
    event_type: pakete_zugestellt
    id: zugestellt
actions:
  - action: notify.mobile_app_mein_handy
    data:
      title: >-
        {{ {'heute': 'Paket kommt heute', 'abholen': 'Paket abholen', 'zugestellt': 'Paket zugestellt'}[trigger.id] }}
      message: "{{ trigger.event.data.dienst }}: {{ trigger.event.data.info }}"
mode: queued
```

`notify.mobile_app_mein_handy` durch den eigenen Notify-Dienst ersetzen.

## Grenzen

- Erkannt wird nur am **Betreff**. Ändert ein Versanddienst seine Betreffzeilen, wird die Mail nicht mehr erkannt. Nicht erkannte Mails stehen mit Log-Level `debug` im Log („nicht erkannt: …“).
- DPD und Hermes nennen im Betreff keine Sendungsnummer. Mehrere Pakete desselben Dienstes werden deshalb gezählt, nicht einzeln zugeordnet.
- Andere Dienste (GLS, UPS, Post) und andere Sprachen werden noch nicht unterstützt.

## Mitmachen

Eine Betreffzeile wird nicht erkannt? Gern ein Issue mit Absender und Betreff (persönliche Daten vorher entfernen) oder direkt einen Pull Request: Die Regeln stehen in `custom_components/pakete/parcels.py`, dazu einen Testfall in `tests/test_parcels.py` ergänzen.

```bash
python3 tests/test_parcels.py
```

## Lizenz

MIT
