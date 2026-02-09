FROM python:3.14-slim

LABEL maintainer="Breitbandmessung Dashboard" \
      description="Web Dashboard für Speedtest-Analyse" \
      version="1.0"

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App kopieren
COPY app.py ./

# Streamlit Konfiguration
RUN mkdir -p ~/.streamlit
RUN echo '[server]\nheadless = true\nport = 8501\nenableXsrfProtection = false\nenableCORS = false\n\n[browser]\ngatherUsageStats = false' > ~/.streamlit/config.toml

# Port
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
