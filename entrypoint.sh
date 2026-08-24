#!/bin/sh
set -u

INTERVAL="${RUN_INTERVAL_SECONDS:-3600}"

echo "$(date '+%Y-%m-%d %H:%M:%S') iGPSport-Downloader gestartet"
echo "Ausführungsintervall: ${INTERVAL} Sekunden"

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') Starte Synchronisierung"

    python3 /app/igpsport_script.py
    EXIT_CODE=$?

    if [ "$EXIT_CODE" -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Synchronisierung abgeschlossen"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') Fehler, Exit-Code ${EXIT_CODE}"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') Nächster Lauf in ${INTERVAL} Sekunden"
    sleep "$INTERVAL"
done
