# Breitbandmessung

**🇬🇧 [English Version](README.md)**

Automatisierte BNetzA-Speedtests mit CSV-Export für [DOCSight](https://github.com/itsdnns/docsight).

Führt über Selenium einen headless Firefox gegen [breitbandmessung.de](https://breitbandmessung.de/test) aus und exportiert die Ergebnisse als CSV — nach konfigurierbarem Zeitplan.

## Features

- Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test) (offizielles BNetzA-Tool)
- CSV-Export für DOCSight Integration (shared Docker Volume)
- Konfigurierbarer Zeitplan über Cron-Ausdrücke
- Optionale Screenshot-Aufnahme der Ergebnisse
- Multi-Architektur Docker Image (amd64, arm64)
- Security-Scanning via CodeQL, Trivy, Hadolint, Bandit

## Schnellstart

```bash
docker compose up -d
```

Oder das fertige Image direkt pullen:

```bash
docker pull ghcr.io/serph91p/breitbandmessung:latest
```

## Konfiguration

Alle Einstellungen werden über Environment-Variablen in der `compose.yaml` konfiguriert:

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `TZ` | `Europe/Berlin` | Zeitzone |
| `CRON_SCHEDULE` | `0 */2 * * *` | Cron-Schedule für Messungen |
| `RUN_ON_STARTUP` | `true` | Bei Container-Start sofort messen |
| `RUN_ONCE` | `false` | Einmalig messen und beenden |
| `SAVE_SCREENSHOTS` | `false` | Screenshots der Ergebnisse speichern |

## Projektstruktur

```
breitbandmessung/
├── src/
│   └── speedtest.py         # Speedtest + CSV-Export
├── compose.yaml              # Docker Compose Konfiguration
├── Dockerfile                # Container-Build
├── entrypoint.sh             # Container-Startpunkt
├── .trivyignore              # Trivy CVE-Ignoreliste
├── .hadolint.yaml            # Dockerfile-Linter-Konfiguration
└── .github/
    └── workflows/
        ├── docker-build.yml  # Build & Push Docker Image
        ├── codeql.yml        # CodeQL Sicherheitsanalyse
        ├── trivy.yml         # Trivy Container- & Dateisystem-Scan
        ├── hadolint.yml      # Dockerfile-Linting
        └── python-security.yml # Bandit + pip-audit
```

## DOCSight Integration

Die CSV-Dateien werden automatisch in ein shared Docker Volume (`shared-bnetz-data`) exportiert. DOCSight's File Watcher importiert diese alle 5 Minuten.

**Voraussetzung:** DOCSight muss dasselbe Volume mounten:

```yaml
# In DOCSight compose.yaml
volumes:
  - bnetz_data:/data/bnetz

volumes:
  bnetz_data:
    name: shared-bnetz-data
```

DOCSight Environment-Variablen:
```
BNETZ_WATCH_ENABLED=true
BNETZ_WATCH_DIR=/data/bnetz
```

## Volumes

| Volume | Beschreibung |
|--------|--------------|
| `breitbandmessung-messprotokolle` | Lokale CSV-Dateien + Screenshots |
| `shared-bnetz-data` | Shared mit DOCSight |

## Logs

```bash
docker logs -f breitbandmessung-speedtest
```

## Sicherheit

Dieses Projekt enthält automatisiertes Security-Scanning:

- **CodeQL** — Statische Analyse für Python Code-Qualität und Sicherheit
- **Trivy** — Container-Image und Dateisystem-Schwachstellenscan
- **Hadolint** — Dockerfile Best-Practices-Linting
- **Bandit** — Python-spezifisches Sicherheits-Linting
- **pip-audit** — Schwachstellenprüfung für Python-Abhängigkeiten

Ergebnisse sind im GitHub Security-Tab einsehbar.

## Lizenz

MIT License
