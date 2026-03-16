FROM python:3.14-alpine

LABEL maintainer="Breitbandmessung" \
      description="Einfacher Speedtest mit CSV-Export" \
      version="3.0-alpine"

ENV PYTHONUNBUFFERED=1 \
    MOZ_HEADLESS=1 \
    GECKODRIVER_VERSION=0.36.0 \
    TZ=Europe/Berlin \
    CRON_SCHEDULE="0 */2 * * *" \
    RUN_ON_STARTUP=true \
    RUN_ONCE=false \
    SAVE_SCREENSHOTS=true \
    EXPORT_PATH=/export \
    DOCSIGHT_EXPORT_PATH=/export/docsight

WORKDIR /usr/src/app

# Installiere nur das Nötigste (Alpine)
# hadolint ignore=DL3018
RUN apk add --no-cache \
    firefox-esr \
    tini \
    tzdata \
    procps-ng

# Installiere Python-Pakete
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir selenium

# Installiere Geckodriver
RUN set -eux; \
    arch="$(uname -m)"; \
    case "${arch}" in \
        x86_64) geckoArch='linux64' ;; \
        aarch64) geckoArch='linux-aarch64' ;; \
        *) echo >&2 "Unsupported arch: ${arch}"; exit 1 ;; \
    esac; \
    wget -q "https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${geckoArch}.tar.gz" -O /tmp/geckodriver.tar.gz; \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/; \
    chmod +x /usr/local/bin/geckodriver; \
    rm /tmp/geckodriver.tar.gz

# Kopiere Dateien
COPY src/speedtest.py ./
COPY entrypoint.sh /usr/local/bin/

# Berechtigungen
RUN chmod +x /usr/src/app/speedtest.py /usr/local/bin/entrypoint.sh && \
    mkdir -p /export && \
    chmod 755 /export

VOLUME ["/export"]

ENTRYPOINT ["tini", "--", "/usr/local/bin/entrypoint.sh"]
