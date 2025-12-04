FROM python:3.11-slim-bullseye

LABEL maintainer="Breitbandmessung" \
      description="Einfacher Speedtest mit CSV-Export" \
      version="3.0-simple"

ENV PYTHONUNBUFFERED=1 \
    MOZ_HEADLESS=1 \
    GECKODRIVER_VERSION=0.34.0

WORKDIR /usr/src/app

# Installiere nur das Nötigste
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    tini \
    cron \
    wget \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Installiere Python-Pakete (nur Selenium benötigt!)
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir selenium

# Installiere Geckodriver
RUN set -eux; \
    dpkgArch="$(dpkg --print-architecture)"; \
    case "${dpkgArch##*-}" in \
        amd64) geckoArch='linux64' ;; \
        arm64) geckoArch='linux-aarch64' ;; \
        *) echo >&2 "Unsupported arch: ${dpkgArch}"; exit 1 ;; \
    esac; \
    wget -q "https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${geckoArch}.tar.gz" -O /tmp/geckodriver.tar.gz; \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/; \
    chmod +x /usr/local/bin/geckodriver; \
    rm /tmp/geckodriver.tar.gz

# Kopiere Dateien
COPY speedtest.py ./
COPY entrypoint.sh /usr/local/bin/
COPY config.ini /usr/src/app/config/config.ini

# Berechtigungen
RUN chmod +x /usr/src/app/speedtest.py /usr/local/bin/entrypoint.sh && \
    mkdir -p /export && \
    chmod 755 /export

VOLUME ["/export"]

ENTRYPOINT ["tini", "--", "/usr/local/bin/entrypoint.sh"]
