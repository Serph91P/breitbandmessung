#!/bin/bash
# Merge-Script für Breitbandmessung CSV-Dateien
# Funktioniert sowohl auf Host als auch im Container

# Bestimme Export-Pfad (Host oder Container)
if [ -d "/export" ]; then
    EXPORT_DIR="/export"  # Im Container
else
    EXPORT_DIR="./messprotokolle"  # Auf Host
fi

OutFileName="${EXPORT_DIR}/messergebnisse.csv"
i=0

for filename in ${EXPORT_DIR}/Breitbandmessung_*.csv; do 
  # Überspringe das Output-File selbst und nicht-existente Files
  if [ "$filename" != "$OutFileName" ] && [ -f "$filename" ]; then 
    if [[ $i -eq 0 ]]; then 
      head -1 "$filename" > "$OutFileName"   # Copy header if it is the first file
      echo "" >> "$OutFileName"              # Ensure newline after header
      echo "📋 Header von: $(basename "$filename")"
    fi
    tail -n +2 "$filename" >> "$OutFileName" # Append from the 2nd line each file
    echo "" >> "$OutFileName"                # Ensure newline after each entry
    i=$(( $i + 1 ))
    echo "  ✓ Merged: $(basename "$filename")"
  fi
done

echo ""
if [ $i -gt 0 ]; then
  echo "✅ $i CSV-Dateien gemerged → $(basename "$OutFileName")"
  echo "📁 Speicherort: $OutFileName"
else
  echo "⚠️  Keine CSV-Dateien gefunden in: $EXPORT_DIR"
fi
