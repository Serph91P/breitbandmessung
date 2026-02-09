# 🚀 Breitbandmessung mit Dashboard

Automatisierte Speedtests mit CSV-Export + FritzBox DOCSIS-Diagnose + **Web-Dashboard**.

## ✨ Features

- ✅ Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test)
- 📊 CSV-Export aller Messergebnisse
- 📡 **FritzBox Cable-Daten** (DOCSIS-Fehler, Signalpegel, etc.)
- 📈 **Web-Dashboard** für interaktive Analyse
- ⏰ Flexibler Zeitplan (Cron)
- 🐳 Docker & Docker Compose

## 📂 Projektstruktur

```
breitbandmessung/
├── dashboard/              # Streamlit Web-Dashboard
│   ├── app.py              # Dashboard-Anwendung
│   ├── Dockerfile          # Dashboard Container
│   └── requirements.txt    # Python-Abhängigkeiten
├── scripts/                # Hilfs-Skripte
│   └── update_data.py      # Datenaufbereitung
├── messprotokolle/         # Gespeicherte Messdaten (Volume)
├── config.ini              # Hauptkonfiguration
├── docker-compose.yml      # Multi-Container Setup
├── speedtest.py            # Speedtest-Logik
├── fritzbox_cable.py       # FritzBox Modul
└── Dockerfile              # Speedtest Container
```

## 🚀 Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/Serph91P/breitbandmessung.git
cd breitbandmessung
```

### 2. Konfiguration anpassen

Bearbeite `config.ini`:

```ini
[Schedule]
cron_schedule = 0 */2 * * *    # Alle 2 Stunden
timezone = Europe/Berlin
run_once = false
run_on_startup = true

[FritzBox]
enabled = true                  # FritzBox-Daten auslesen
host = 192.168.178.1
username = admin
password = dein_passwort
```

### 3. Umgebungsvariablen setzen

```bash
cp .env.example .env
```

Bearbeite `.env`:

```env
EXPORT_PATH=./messprotokolle
DASHBOARD_PORT=8501
```

### 4. Container starten

```bash
# Alles starten (Speedtest + Dashboard)
docker compose up -d

# Nur Dashboard starten
docker compose up -d dashboard

# Nur Speedtest starten
docker compose up -d speedtest
```

### 5. Dashboard öffnen

Öffne im Browser: **http://localhost:8501**

## 📊 Dashboard Features

Das Web-Dashboard bietet:

- **Übersicht**: KPIs und wichtigste Statistiken
- **Zeitverlauf**: Download/Upload-Geschwindigkeit über Zeit
- **Tageszeit-Analyse**: Performance nach Uhrzeit
- **DOCSIS-Analyse**: FritzBox Fehlerauswertung
- **Korrelation**: Zusammenhang Fehler ↔ Geschwindigkeit
- **Probleme**: Liste der schlechtesten Messungen
- **Rohdaten**: Export als CSV

## 🔧 Konfiguration

### config.ini

| Sektion | Option | Beschreibung |
|---------|--------|--------------|
| `[Schedule]` | `cron_schedule` | Cron-Ausdruck für Zeitplan |
| | `timezone` | Zeitzone |
| | `run_once` | Einmalig ausführen (true/false) |
| | `run_on_startup` | Bei Start messen |
| `[FritzBox]` | `enabled` | FritzBox-Daten auslesen |
| | `host` | FritzBox IP-Adresse |
| | `username` | FritzBox Benutzer |
| | `password` | FritzBox Passwort |
| `[Settings]` | `export_path` | Pfad für CSV-Dateien |
| | `save_screenshots` | Screenshots speichern |

### Umgebungsvariablen (.env)

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `EXPORT_PATH` | `./messprotokolle` | Speicherort für Messdaten |
| `DASHBOARD_PORT` | `8501` | Port für Web-Dashboard |

## 📡 FritzBox Integration

Bei aktivierter FritzBox-Integration werden zusätzliche Daten erfasst:

- **DOCSIS Downstream**: Signalpegel, MER/MSE, korrigierbare/nicht-korrigierbare Fehler
- **DOCSIS Upstream**: Sendepegel pro Kanal
- **Verbindungsinfo**: IP, Verbindungsdauer, max. Geschwindigkeit
- **Fehleranalyse**: Problem-Kanäle, Fehlerzuwachs

Diese Daten werden in der CSV mit `FB_*` Präfix gespeichert.

## 🛠️ Entwicklung

### Manuell Daten aktualisieren

```bash
python scripts/update_data.py ./messprotokolle
```

### Dashboard lokal starten

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Container neu bauen

```bash
docker compose build --no-cache
docker compose up -d
```

## 📋 Logs

```bash
# Speedtest Logs
docker logs -f breitbandmessung-speedtest

# Dashboard Logs
docker logs -f breitbandmessung-dashboard
```

## 🆘 Troubleshooting

### Dashboard zeigt "Keine Daten"
- Prüfe ob `messprotokolle/` Ordner existiert und CSV-Dateien enthält
- Führe mindestens eine Messung durch

### FritzBox-Daten fehlen
- Prüfe `[FritzBox] enabled = true` in config.ini
- Prüfe Zugangsdaten (username/password)
- Stelle sicher dass FritzBox erreichbar ist

### Container startet nicht
```bash
docker compose logs speedtest
docker compose logs dashboard
```

## 📄 Lizenz

MIT License
