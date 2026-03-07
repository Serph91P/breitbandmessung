#!/bin/bash
set -e

echo "=========================================="
echo "  🚀 Breitbandmessung"
echo "=========================================="
echo ""

# Lade Einstellungen aus Environment (Defaults im Dockerfile)
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
    
    # Validiere Cron-Schedule
    if [ -z "$CRON_SCHEDULE" ]; then
        echo "❌ FEHLER: Kein Cron-Schedule konfiguriert!"
        echo "Setze CRON_SCHEDULE in der compose.yaml"
        exit 1
    fi
    
    echo "📅 Cron Schedule: '$CRON_SCHEDULE'"
    
    # Exportiere Umgebung für Cron (Werte quoten wegen Sonderzeichen wie * im Schedule)
    printenv | sed 's/\([^=]*\)=\(.*\)/export \1="\2"/' > /root/env.sh
    
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