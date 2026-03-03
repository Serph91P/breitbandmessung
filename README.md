# Breitbandmessung

**🇩🇪 [Deutsche Version](README.de.md)**

Automated BNetzA (German Federal Network Agency) speed tests with CSV export for [DOCSight](https://github.com/itsdnns/docsight).

Runs headless Firefox via Selenium against [breitbandmessung.de](https://breitbandmessung.de/test) on a configurable schedule and exports results as CSV.

## Features

- Automated speed tests via [breitbandmessung.de](https://breitbandmessung.de/test) (official BNetzA tool)
- CSV export for DOCSight integration (shared Docker volume)
- Configurable schedule via cron expressions
- Optional screenshot capture of results
- Multi-architecture Docker image (amd64, arm64)
- Security scanning via CodeQL, Trivy, Hadolint, Bandit

## Quick Start

```bash
docker compose up -d
```

Or pull the pre-built image directly:

```bash
docker pull ghcr.io/serph91p/breitbandmessung:latest
```

## Configuration

All settings are configured via environment variables in `compose.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `Europe/Berlin` | Timezone |
| `CRON_SCHEDULE` | `0 */2 * * *` | Cron schedule for measurements |
| `RUN_ON_STARTUP` | `true` | Run a measurement immediately on container start |
| `RUN_ONCE` | `false` | Run a single measurement and exit |
| `SAVE_SCREENSHOTS` | `false` | Save screenshots of test results |

## Project Structure

```
breitbandmessung/
├── src/
│   └── speedtest.py         # Speed test + CSV export
├── compose.yaml              # Docker Compose configuration
├── Dockerfile                # Container build
├── entrypoint.sh             # Container entrypoint
├── .trivyignore              # Trivy CVE ignore list
├── .hadolint.yaml            # Dockerfile linter config
└── .github/
    └── workflows/
        ├── docker-build.yml  # Build & push Docker image
        ├── codeql.yml        # CodeQL security analysis
        ├── trivy.yml         # Trivy container & filesystem scan
        ├── hadolint.yml      # Dockerfile linting
        └── python-security.yml # Bandit + pip-audit
```

## DOCSight Integration

CSV files are automatically exported to a shared Docker volume (`shared-bnetz-data`). DOCSight's File Watcher imports these every 5 minutes.

**Prerequisite:** DOCSight must mount the same volume:

```yaml
# In DOCSight compose.yaml
volumes:
  - bnetz_data:/data/bnetz

volumes:
  bnetz_data:
    name: shared-bnetz-data
```

DOCSight environment variables:
```
BNETZ_WATCH_ENABLED=true
BNETZ_WATCH_DIR=/data/bnetz
```

## Volumes

| Volume | Description |
|--------|-------------|
| `breitbandmessung-messprotokolle` | Local CSV files + screenshots |
| `shared-bnetz-data` | Shared with DOCSight |

## Logs

```bash
docker logs -f breitbandmessung-speedtest
```

## Security

This project includes automated security scanning:

- **CodeQL** — Static analysis for Python code quality and security
- **Trivy** — Container image and filesystem vulnerability scanning
- **Hadolint** — Dockerfile best practices linting
- **Bandit** — Python-specific security linting
- **pip-audit** — Python dependency vulnerability checking

Results are available in the GitHub Security tab.

## License

MIT License
