#!/usr/bin/env python3
"""
Importiert bestehende CSV-Dateien in die SQLite-Datenbank.
Wird einmalig ausgeführt oder bei Bedarf.
"""

import os
import sys
import csv
import glob
from pathlib import Path

# DB-Modul importieren
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import init_db, insert_measurement, get_db_path


def clean_value(val):
    """Entfernt Anführungszeichen und konvertiert Dezimalformat"""
    if val is None:
        return None
    val = str(val).strip().replace('"', '')
    return val if val else None


def clean_float(val):
    """Konvertiert deutschen Dezimalwert zu Float"""
    val = clean_value(val)
    if not val:
        return None
    try:
        return float(val.replace(',', '.'))
    except (ValueError, AttributeError):
        return None


def clean_int(val):
    """Konvertiert zu Integer"""
    val = clean_value(val)
    if not val:
        return None
    try:
        return int(float(val))
    except (ValueError, AttributeError):
        return None


def import_csv(csv_path, db_path=None):
    """Importiert eine einzelne CSV-Datei"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                date = clean_value(row.get('Messzeitpunkt', ''))
                time_val = clean_value(row.get('Uhrzeit', ''))
                
                if not date or not time_val:
                    continue
                
                # Datetime zusammenbauen (DD.MM.YYYY HH:MM:SS → YYYY-MM-DD HH:MM:SS)
                try:
                    parts = date.split('.')
                    iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    dt = f"{iso_date} {time_val}"
                except (IndexError, ValueError):
                    dt = f"{date} {time_val}"
                
                data = {
                    'test_id': clean_value(row.get('Test-ID', '')),
                    'datetime': dt,
                    'date': date,
                    'time': time_val,
                    'download_mbps': clean_float(row.get('Download (Mbit/s)')),
                    'upload_mbps': clean_float(row.get('Upload (Mbit/s)')),
                    'ping_ms': clean_float(row.get('Laufzeit (ms)')),
                    'version': clean_value(row.get('Version', '')),
                    'os': clean_value(row.get('Betriebssystem', '')),
                    'browser': clean_value(row.get('Internet-Browser', '')),
                    
                    # FritzBox-Daten (falls vorhanden)
                    'fb_non_corr_errors': clean_int(row.get('FB_Non_Corr_Errors')),
                    'fb_corr_errors': clean_int(row.get('FB_Corr_Errors')),
                    'fb_docsis31_ds': clean_int(row.get('FB_DOCSIS31_DS')),
                    'fb_docsis30_ds': clean_int(row.get('FB_DOCSIS30_DS')),
                    'fb_docsis31_us': clean_int(row.get('FB_DOCSIS31_US')),
                    'fb_docsis30_us': clean_int(row.get('FB_DOCSIS30_US')),
                    'fb_avg_ds_power': clean_float(row.get('FB_Avg_DS_Power_dBmV')),
                    'fb_min_ds_power': clean_float(row.get('FB_Min_DS_Power_dBmV')),
                    'fb_max_ds_power': clean_float(row.get('FB_Max_DS_Power_dBmV')),
                    'fb_avg_us_power': clean_float(row.get('FB_Avg_US_Power_dBmV')),
                    'fb_sync_ds_kbps': clean_int(row.get('FB_Sync_DS_Kbps')),
                    'fb_sync_us_kbps': clean_int(row.get('FB_Sync_US_Kbps')),
                    'fb_connection_time': clean_value(row.get('FB_Connection_Time', '')),
                    'fb_top_problem_channel': clean_int(row.get('FB_Top_Problem_Channel')),
                    'fb_top_problem_errors': clean_int(row.get('FB_Top_Problem_Errors')),
                }
                
                result = insert_measurement(data, db_path)
                return result is not None  # True = inserted, False = duplicate
                
    except Exception as e:
        print(f"  ⚠️ Fehler bei {os.path.basename(csv_path)}: {e}")
        return False


def import_all(data_dir, db_path=None):
    """Importiert alle CSVs aus einem Verzeichnis"""
    if db_path:
        os.environ["DB_PATH"] = db_path
    
    actual_db = db_path or get_db_path()
    print(f"📂 Datenverzeichnis: {data_dir}")
    print(f"💾 Datenbank: {actual_db}")
    
    # DB initialisieren
    init_db(actual_db)
    
    # Finde alle Mess-CSVs (ohne _docsis und _fritzbox)
    all_csvs = sorted(glob.glob(os.path.join(data_dir, "Breitbandmessung_*.csv")))
    measurement_csvs = [f for f in all_csvs 
                        if not f.endswith('_docsis.csv') 
                        and not f.endswith('_fritzbox_full.json')]
    
    print(f"📊 {len(measurement_csvs)} CSV-Dateien gefunden")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for i, csv_path in enumerate(measurement_csvs):
        result = import_csv(csv_path, actual_db)
        if result is True:
            imported += 1
        elif result is False:
            skipped += 1
        else:
            errors += 1
        
        # Fortschritt alle 100 Dateien
        if (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(measurement_csvs)} verarbeitet")
    
    print(f"\n✅ Import abgeschlossen:")
    print(f"  📥 Importiert: {imported}")
    print(f"  ⏭️  Übersprungen (Duplikate): {skipped}")
    if errors:
        print(f"  ❌ Fehler: {errors}")


if __name__ == "__main__":
    # Standard: /export (im Container) oder Argument
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/export"
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    import_all(data_dir, db_path)
