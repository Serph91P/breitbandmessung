# Breitbandmessung - AI Coding Assistant Instructions

## Project Overview
Automated internet speed measurement tool for German ISP customers using bundesnetzagentur.de's Breitbandmessung service. Dockerized Python application that runs headless Selenium tests via Firefox, exports results to CSV/screenshots, and optionally reports to notification services (Telegram, email, Twitter) and metrics backends (InfluxDB v1/v2, Prometheus).

## Architecture & Key Components

### Entry Point Flow
1. **`entrypoint.sh`** - Container initialization
   - Sources `config.shlib` for config parsing
   - Reads `[General]` section for runtime behavior (timezone, cron schedule, run_once, run_on_startup)
   - Sets up cron or runs once based on configuration
   - All config keys fallback to defaults if not found

2. **`speedtest.py`** - Core measurement script
   - Selenium-based web automation (headless Firefox)
   - Reads INI-style config from `/usr/src/app/config/config.cfg`
   - Downloads CSV results from breitbandmessung.de
   - Parses German decimal format (`,` to `.` conversion)
   - Saves screenshots to `/export/` directory

3. **`config.shlib`** - Config parsing library
   - Bash functions for reading INI files: `config_get(key, section)`
   - Cascading config: user config → defaults → hardcoded fallbacks
   - Handles section-based config (e.g., `[General]`, `[Measurement]`, `[Telegram]`)

### Configuration System
- **INI format** with sections: `[General]`, `[Measurement]`, `[Telegram]`, `[MAIL]`, `[Twitter]`, `[influxdb]`, `[influxdbv2]`, `[prometheus]`
- User config mounted at: `/usr/src/app/config/config.cfg`
- Defaults file: `config.cfg.defaults` (copied to `config/config.cfg` by `create.sh`)
- Critical: Config values are section-aware; shell scripts use `[General]`, Python reads all sections

### Data Flow
1. **Input**: Config file determines thresholds, notification channels, metrics backends
2. **Processing**: Selenium automates breitbandmessung.de test → downloads CSV → parses values
3. **Output**: 
   - CSV files in `/export/` (mounted to `messprotokolle/` on host)
   - Screenshots (`.png`) for each measurement
   - Optional notifications if speed < thresholds
   - Optional metrics push to InfluxDB/Prometheus

### External Dependencies
- **Selenium + geckodriver**: Automated browser control (Firefox ESR)
- **InfluxDB clients**: Two versions supported (v1 and v2 APIs)
- **Prometheus client**: Optional metrics push via Pushgateway
- **Apprise**: Unified notification abstraction (Telegram, email, Twitter)
- **Rust toolchain**: Required to compile cryptography wheel during Docker build

## Critical Workflows

### Build & Run
```bash
# Standard setup (Linux/Mac)
./create.sh  # Builds image, creates directories, copies default config

# Manual Docker
docker build -f Dockerfile -t breitbandmessung .
docker run -v ./config:/usr/src/app/config:rw -v ./messprotokolle:/export:rw breitbandmessung
```

### Configuration Changes
- Edit `config/config.cfg` on host (persisted via volume mount)
- Restart container to apply: `docker restart breitbandmessung`
- Set `run_once=false` + configure `crontab` for scheduled measurements
- Example cron: `0 */2 * * *` (every 2 hours)

### Debugging
- View logs: `docker logs -f breitbandmessung`
- Screenshots saved on errors (filename includes `_error_`)
- Firefox profile cleanup: `cleanup_firefox_profiles()` removes `/tmp/rust_mozprofile*`

## Project-Specific Conventions

### German Decimal Handling
All CSV parsing converts `,` to `.` for float operations:
```python
float(result_down.text.replace(",", "."))
```

### Mock Elements Pattern
After CSV download, values are wrapped in `MockElement` objects to mimic Selenium's element interface:
```python
class MockElement:
    def __init__(self, text):
        self.text = text
```

### Browser Cleanup
Always call `closebrowser()` which:
1. Kills stale Firefox processes via `ps` + `SIGKILL`
2. Cleans up temporary Firefox profiles in `/tmp`

### Notification Conditions
Only triggers notifications if:
- `[Measurement]` section exists with `min-upload` and `min-download`
- Measured speed < thresholds
- At least one notification service configured

### Metrics Export
- **InfluxDB**: Writes 3 measurements (download, upload, ping) with timestamps in UTC
- **Prometheus**: Pushes 3 gauges (`breitbandmessung_download_mbps`, `breitbandmessung_upload_mbps`, `breitbandmessung_ping_ms`)

## File Structure Patterns
- Shell scripts use absolute paths: `/usr/src/app/`
- Volume mounts: `/usr/src/app/config` (config), `/export` (results)
- Screenshots: `Breitbandmessung_{date}_{time}.png` format
- CSV format: Semicolon-delimited with German locale headers

## Common Tasks

### Adding New Notification Channels
1. Add config section in `config.cfg.defaults`
2. Read config in `speedtest.py` after existing notification blocks
3. Use Apprise URL scheme: `apobj.add("scheme://credentials")`

### Extending Metrics Backends
1. Add optional import with try/except (like `prometheus_client`)
2. Read config section in main config block
3. Add export logic after InfluxDB/Prometheus blocks (around line 290)

### Modifying Selenium Selectors
- All CSS selectors defined as module-level constants (e.g., `allow_necessary`, `start_test_button`)
- Update if breitbandmessung.de changes layout
- Test with `run_on_startup=true` and `run_once=true` for quick validation
