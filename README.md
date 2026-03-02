# Breitbandmessung

Automatisierte BNetzA-Speedtests mit CSV-Export für [DOCSight](https://github.com/itsdnns/docsight).

## Features

- Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test)
- CSV-Export für DOCSight BNetzA Integration (shared Volume)
- Flexibler Zeitplan (Cron) via Environment-Variablen
- Docker & Docker Compose

## Projektstruktur

```
breitbandmessung/
├── src/
│   └── speedtest.py        # Speedtest + DOCSight CSV-Export
├── compose.yaml            # Docker Compose
├── Dockerfile              # Container
└── entrypoint.sh           # Container Startpunkt
```

## Schnellstart

```bash
docker compose up -d
```

Konfiguration über Environment-Variablen in der `compose.yaml`:

```yaml
environment:
  - TZ=Europe/Berlin
  - CRON_SCHEDULE=0 */2 * * *
  - RUN_ON_STARTUP=true
  - RUN_ONCE=false
  - SAVE_SCREENSHOTS=true
```

## DOCSight Integration

Die CSVs werden automatisch in ein shared Docker Volume (`shared-bnetz-data`) exportiert. DOCSight's File Watcher importiert diese alle 5 Minuten.

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

## Environment-Variablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `TZ` | `Europe/Berlin` | Zeitzone |
| `CRON_SCHEDULE` | `0 */2 * * *` | Cron-Schedule für Messungen |
| `RUN_ON_STARTUP` | `true` | Bei Start sofort messen |
| `RUN_ONCE` | `false` | Einmalig messen und beenden |
| `SAVE_SCREENSHOTS` | `true` | Screenshots speichern |

## Volumes

| Volume | Beschreibung |
|--------|--------------|
| `breitbandmessung-messprotokolle` | Lokale CSV-Dateien + Screenshots |
| `shared-bnetz-data` | Shared mit DOCSight |

## Logs

```bash
docker logs -f breitbandmessung-speedtest
```

## Lizenz

MIT License
