#!/bin/bash
set -e

echo "=========================================="
echo "  🚀 Breitbandmessung"
echo "=========================================="
echo ""

# Lese Config
CONFIG_FILE="/usr/src/app/config/config.ini"

# Einfache INI-Parsing-Funktion
get_config() {
    local key=$1
    local section=$2
    grep -A 20 "\[$section\]" "$CONFIG_FILE" | grep "^$key" | cut -d'=' -f2 | tr -d ' '
}

# Lade Einstellungen
TZ=$(get_config "timezone" "Schedule")
CRON_SCHEDULE=$(get_config "cron_schedule" "Schedule")
RUN_ONCE=$(get_config "run_once" "Schedule")
RUN_ON_STARTUP=$(get_config "run_on_startup" "Schedule")

echo "⚙️  Konfiguration:"
echo "  🌍 Zeitzone:     $TZ"
echo "  ⏰ Schedule:     $CRON_SCHEDULE"
echo "  🔄 Run Once:     $RUN_ONCE"
echo "  🚀 On Startup:   $RUN_ON_STARTUP"
echo ""

# Setze Zeitzone
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "✓ Zeitzone: $TZ"
fi

export MOZ_HEADLESS=1

# Bei Startup ausführen?
if [ "$RUN_ON_STARTUP" = "true" ]; then
    echo "=========================================="
    echo "  ▶️  Starte Messung..."
    echo "=========================================="
    /usr/src/app/speedtest.py
    
    # Nur einmal?
    if [ "$RUN_ONCE" = "true" ]; then
        echo ""
        echo "✅ Fertig! Container stoppt."
        exit 0
    fi
fi

# Dauerhaft laufen?
if [ "$RUN_ONCE" = "false" ]; then
    echo "=========================================="
    echo "  ⏰ Richte Cron ein..."
    echo "=========================================="
    
    # Exportiere Umgebung für Cron
    printenv | sed 's/^\(.*\)$/export \1/g' > /root/env.sh
    
    # Erstelle Cron-Job
    echo "$CRON_SCHEDULE . /root/env.sh && /usr/src/app/speedtest.py" | crontab -
    
    echo "✓ Cron Schedule: $CRON_SCHEDULE"
    echo ""
    echo "Container läuft dauerhaft..."
    echo "Nächste Messung gemäß Zeitplan"
    echo ""
    
    # Starte Cron
    cron -f
else
    echo "Einmal-Modus - führe Messung durch..."
    /usr/src/app/speedtest.py
    exit 0
fi