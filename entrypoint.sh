#!/bin/bash
set -e

echo "=========================================="
echo "  🚀 Breitbandmessung"
echo "=========================================="
echo ""

# Config: Falls keine config.ini vorhanden, nutze Default
CONFIG_FILE="/usr/src/app/config/config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ℹ️  Keine config.ini gefunden, nutze Defaults"
    cp /usr/src/app/config/config.ini.default "$CONFIG_FILE"
fi

# Einfache INI-Parsing-Funktion
get_config() {
    local key=$1
    local section=$2
    # Lese Wert und entferne nur führende/nachfolgende Leerzeichen
    grep -A 20 "\[$section\]" "$CONFIG_FILE" | grep "^$key" | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/#.*//'
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

# Datenbank: Initialisieren und ggf. CSV-Import
DB_FILE="/export/measurements.db"
if [ ! -f "$DB_FILE" ]; then
    echo "=========================================="
    echo "  💾 Initialisiere Datenbank..."
    echo "=========================================="
    CSV_COUNT=$(find /export -name "Breitbandmessung_*.csv" ! -name "*_docsis.csv" 2>/dev/null | wc -l)
    if [ "$CSV_COUNT" -gt 0 ]; then
        echo "📊 $CSV_COUNT bestehende CSV-Dateien gefunden, importiere..."
        python3 /usr/src/app/import_csv.py /export "$DB_FILE"
    else
        echo "ℹ️  Keine bestehenden CSV-Dateien, DB wird beim ersten Test erstellt"
    fi
    echo ""
fi

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
    
    # Validiere Cron-Schedule
    if [ -z "$CRON_SCHEDULE" ]; then
        echo "❌ FEHLER: Kein Cron-Schedule konfiguriert!"
        echo "Bitte prüfe config.ini"
        exit 1
    fi
    
    echo "📅 Cron Schedule: '$CRON_SCHEDULE'"
    
    # Exportiere Umgebung für Cron
    printenv | sed 's/^\(.*\)$/export \1/g' > /root/env.sh
    
    # Erstelle Cron-Job
    echo "$CRON_SCHEDULE . /root/env.sh && /usr/src/app/speedtest.py >> /proc/1/fd/1 2>&1" | crontab -
    
    # Prüfe ob Crontab erfolgreich war
    if [ $? -ne 0 ]; then
        echo "❌ FEHLER: Ungültiger Cron-Schedule!"
        echo "Format: Minute Stunde Tag Monat Wochentag"
        echo "Beispiel: 0 */2 * * *"
        exit 1
    fi
    
    echo "✓ Cron eingerichtet"
    echo ""
    echo "📊 Aktuelle Crontab:"
    crontab -l
    echo ""
    echo "🔄 Container läuft dauerhaft..."
    echo "   Nächste Messung gemäß Zeitplan"
    echo ""
    
    # Starte Cron
    cron -f
else
    echo "🔄 Einmal-Modus - führe Messung durch..."
    /usr/src/app/speedtest.py
    echo ""
    echo "✅ Container beendet sich"
    exit 0
fi