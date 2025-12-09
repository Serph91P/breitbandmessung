#!/usr/local/bin/python3
"""
Breitbandmessung - Einfacher Speedtest mit CSV-Export
Führt automatisierte Messungen über breitbandmessung.de durch

Version 2.0 - Mit verbesserter FritzBox Cable Integration
"""
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime
import configparser
import time
import subprocess
import signal
import os
import csv
import glob
import shutil
import json

# FritzBox Cable Modul (neues verbessertes Modul)
try:
    from fritzbox_cable import FritzBoxCable
    FRITZBOX_MODULE_AVAILABLE = True
except ImportError:
    FRITZBOX_MODULE_AVAILABLE = False
    print("⚠️  fritzbox_cable.py nicht gefunden - FritzBox-Integration eingeschränkt")

# Lade Konfiguration
config = configparser.ConfigParser()
config.read("/usr/src/app/config/config.ini")

# Einstellungen aus Config
EXPORT_PATH = config.get("Settings", "export_path", fallback="/export")
SLEEPTIME = config.getint("Settings", "wait_time", fallback=10)
SAVE_SCREENSHOTS = config.getboolean("Settings", "save_screenshots", fallback=True)

# FritzBox Settings (optional)
FRITZBOX_ENABLED = config.getboolean("FritzBox", "enabled", fallback=False)
FRITZBOX_HOST = config.get("FritzBox", "host", fallback="192.168.178.1")
FRITZBOX_USER = config.get("FritzBox", "username", fallback="")
FRITZBOX_PASSWORD = config.get("FritzBox", "password", fallback="")
FRITZBOX_SCREENSHOT = config.getboolean("FritzBox", "screenshot_cable_page", fallback=True)

# Konstanten
TEST_URL = "https://breitbandmessung.de/test"
FIREFOX_PATH = "firefox-esr"
GECKODRIVER_PATH = "/usr/local/bin/geckodriver"


# CSS Selectors für Buttons
ALLOW_NECESSARY = "#allow-necessary"
START_TEST_BUTTON = "button.btn:nth-child(4)"
ALLOW_BUTTON = "button.btn:nth-child(2)"
WEBSITE_HEADER = "#root > div > div > div > div > div:nth-child(1) > h1"
DOWNLOAD_RESULT = "button.px-0:nth-child(1)"


def get_fritzbox_cable_info():
    """
    Liest ALLE verfügbaren Kabel-Daten von der FritzBox aus.
    Nutzt das neue FritzBoxCable-Modul mit Session-basiertem Login.
    
    Sammelt:
    - DOCSIS Kanaldaten (Fehler, Signalpegel, MER/MSE)
    - Kabel-Übersicht (Geschwindigkeit, Verbindungsstatus)
    - Verbindungsinfo (IP, Verbindungsdauer)
    - Traffic-Daten (aktuelle Auslastung)
    """
    if not FRITZBOX_ENABLED:
        return None
    
    if not FRITZBOX_MODULE_AVAILABLE:
        print("⚠️  FritzBox-Modul nicht verfügbar", flush=True)
        return None
    
    try:
        print("\n📡 Lese FritzBox Daten (ALLE verfügbaren)...", flush=True)
        
        # Nutze das neue Modul mit Session-basiertem Login
        with FritzBoxCable(FRITZBOX_HOST, FRITZBOX_USER, FRITZBOX_PASSWORD) as fb:
            # Hole ALLE Daten
            all_data = fb.get_all_cable_data()
            
            if not all_data['success']:
                print("❌ Konnte keine Daten abrufen", flush=True)
                return None
            
            parsed = all_data['parsed']
            cable_ov = all_data.get('cable_overview') or {}
            connection = all_data.get('connection') or {}
            traffic = all_data.get('traffic') or {}
            
            # Extrahiere Kabel-Übersicht Daten
            ds_speed = 0
            us_speed = 0
            connection_time = ""
            
            if cable_ov:
                # Versuche Geschwindigkeiten zu extrahieren
                if 'downstream' in cable_ov:
                    ds_speed = cable_ov.get('downstream', {}).get('currentRate', 0)
                if 'upstream' in cable_ov:
                    us_speed = cable_ov.get('upstream', {}).get('currentRate', 0)
                connection_time = cable_ov.get('connectionTime', '')
            
            # Extrahiere Traffic-Daten (aktuelle Auslastung)
            current_ds_bps = 0
            current_us_bps = 0
            
            if traffic:
                # Traffic kann verschiedene Formate haben
                if 'downstream' in traffic:
                    current_ds_bps = traffic.get('downstream', {}).get('currentBps', 0)
                if 'upstream' in traffic:
                    current_us_bps = traffic.get('upstream', {}).get('currentBps', 0)
            
            # Baue umfassendes Ergebnis
            cable_info = {
                'source': 'fritzbox_cable_module_v2',
                'timestamp': all_data['timestamp'],
                
                # DOCSIS Fehlerstatistik
                'total_non_corr_errors': parsed['summary']['total_non_corr_errors'],
                'total_corr_errors': parsed['summary']['total_corr_errors'],
                'problem_channels': parsed['summary']['problem_channels'],
                
                # Kanalzählung
                'docsis31_ds_channels': len(parsed['downstream']['docsis31']),
                'docsis30_ds_channels': len(parsed['downstream']['docsis30']),
                'docsis31_us_channels': len(parsed['upstream']['docsis31']),
                'docsis30_us_channels': len(parsed['upstream']['docsis30']),
                
                # Detaillierte Kanaldaten
                'downstream_channels': parsed['downstream']['docsis31'] + parsed['downstream']['docsis30'],
                'upstream_channels': parsed['upstream']['docsis31'] + parsed['upstream']['docsis30'],
                
                # Kabel-Übersicht
                'sync_ds_speed_kbps': ds_speed,
                'sync_us_speed_kbps': us_speed,
                'connection_time': connection_time,
                
                # Aktuelle Auslastung
                'current_ds_bps': current_ds_bps,
                'current_us_bps': current_us_bps,
                
                # Rohdaten für spätere Analyse
                'raw_all_data': all_data
            }
            
            # Berechne durchschnittliche Signalwerte
            ds_power_levels = [ch.get('power_level', 0) for ch in cable_info['downstream_channels']]
            if ds_power_levels:
                cable_info['avg_ds_power_level'] = sum(ds_power_levels) / len(ds_power_levels)
                cable_info['min_ds_power_level'] = min(ds_power_levels)
                cable_info['max_ds_power_level'] = max(ds_power_levels)
            
            us_power_levels = [ch.get('power_level', 0) for ch in cable_info['upstream_channels']]
            if us_power_levels:
                cable_info['avg_us_power_level'] = sum(us_power_levels) / len(us_power_levels)
            
            # Zeige Zusammenfassung
            print(f"✓ FritzBox Daten gelesen", flush=True)
            print(f"  📊 DOCSIS 3.1: {cable_info['docsis31_ds_channels']} DS / {cable_info['docsis31_us_channels']} US Kanäle", flush=True)
            print(f"  📊 DOCSIS 3.0: {cable_info['docsis30_ds_channels']} DS / {cable_info['docsis30_us_channels']} US Kanäle", flush=True)
            print(f"  🔴 Nicht korrigierbar: {cable_info['total_non_corr_errors']:,}", flush=True)
            print(f"  🟡 Korrigiert: {cable_info['total_corr_errors']:,}", flush=True)
            if ds_speed:
                print(f"  📶 Sync-Geschwindigkeit: {ds_speed/1000:.0f} Mbit/s DS / {us_speed/1000:.0f} Mbit/s US", flush=True)
            if connection_time:
                print(f"  ⏱️  Verbindungsdauer: {connection_time}", flush=True)
            
            # Zeige Problem-Kanäle
            if cable_info['problem_channels']:
                print(f"  🚨 PROBLEM-KANÄLE:", flush=True)
                for ch in cable_info['problem_channels'][:3]:  # Top 3
                    print(f"     Kanal {ch['channel_id']}: {ch['non_corr_errors']:,} Fehler", flush=True)
            
            return cable_info
            
    except Exception as e:
        print(f"⚠️  FritzBox API Fehler: {e}", flush=True)
def cleanup_firefox():
    """Räume alte Firefox-Prozesse und Profile auf"""
    try:
        # Beende alte Firefox-Prozesse
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            if FIREFOX_PATH.encode() in line:
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)
        
        # Lösche alte Firefox-Profile
        profile_dirs = glob.glob('/tmp/rust_mozprofile*')
        for profile_dir in profile_dirs:
            shutil.rmtree(profile_dir, ignore_errors=True)
    except Exception as e:
        print(f"⚠️  Cleanup-Fehler: {e}", flush=True)


def ensure_export_directory():
    """Stelle sicher, dass das Export-Verzeichnis existiert"""
    if not os.path.exists(EXPORT_PATH):
        os.makedirs(EXPORT_PATH, exist_ok=True)
        print(f"✓ Export-Verzeichnis erstellt: {EXPORT_PATH}", flush=True)
    else:
        print(f"✓ Export-Verzeichnis: {EXPORT_PATH}", flush=True)

def run_speedtest():
    """Führt einen Speedtest durch und speichert die Ergebnisse als CSV"""
    
    print("=" * 50)
    print("🚀 Starte Breitbandmessung...")
    print("=" * 50)
    
    # Browser konfigurieren
    print("\n🌐 Öffne Browser...")
    options = webdriver.FirefoxOptions()
    options.headless = True
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", EXPORT_PATH)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/force-download")
    options.set_preference("browser.download.panel.shown", False)
    options.binary_location = FIREFOX_PATH
    
    service = Service(executable_path=GECKODRIVER_PATH)
    browser = webdriver.Firefox(service=service, options=options)
    
    try:
        # Öffne Test-Seite
        browser.get(TEST_URL)
        print("✓ Seite geladen")
        
        # Cookies akzeptieren
        print("\n🍪 Akzeptiere Cookies...")
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ALLOW_NECESSARY))
        )
        browser.find_element(By.CSS_SELECTOR, ALLOW_NECESSARY).click()
        
        # Warte auf Standort-Dialog
        time.sleep(SLEEPTIME)
        
        # Starte Test
        print("\n▶️  Starte Messung...")
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, START_TEST_BUTTON))
        )
        browser.find_element(By.CSS_SELECTOR, START_TEST_BUTTON).click()
        browser.find_element(By.CSS_SELECTOR, ALLOW_BUTTON).click()
        
        # Warte auf Abschluss
        print("⏳ Messung läuft (dauert ca. 1-2 Minuten)...")
        while True:
            time.sleep(SLEEPTIME)
            header = browser.find_element(By.CSS_SELECTOR, WEBSITE_HEADER)
            if "abgeschlossen" in header.text:
                print("✓ Messung abgeschlossen!")
                break
        
        # Lade CSV herunter
        print("\n💾 Lade CSV-Datei herunter...")
        browser.find_element(By.CSS_SELECTOR, DOWNLOAD_RESULT).click()
        time.sleep(3)
        
        # Finde neueste CSV-Datei
        csv_files = glob.glob(os.path.join(EXPORT_PATH, "*.csv"))
        if not csv_files:
            raise FileNotFoundError("❌ Keine CSV-Datei gefunden!")
        
        latest_csv = max(csv_files, key=os.path.getctime)
        
        # Lese Ergebnisse
        with open(latest_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            data = next(reader)
            
            download = data['Download (Mbit/s)'].replace(',', '.')
            upload = data['Upload (Mbit/s)'].replace(',', '.')
            ping = data['Laufzeit (ms)']
        
        # Hole FritzBox Cable-Daten
        fritzbox_data = get_fritzbox_cable_info()
        
        # Erweitere CSV mit FritzBox DOCSIS-Daten (ALLE Daten für maximale Dokumentation)
        if fritzbox_data:
            # Lese komplette CSV
            with open(latest_csv, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Erweitere Header mit ALLEN relevanten Daten
            header = lines[0].strip()
            # Fehlerstatistik
            header += ';FB_Non_Corr_Errors;FB_Corr_Errors'
            # Kanalzählung
            header += ';FB_DOCSIS31_DS;FB_DOCSIS30_DS;FB_DOCSIS31_US;FB_DOCSIS30_US'
            # Signalpegel
            header += ';FB_Avg_DS_Power_dBmV;FB_Min_DS_Power_dBmV;FB_Max_DS_Power_dBmV;FB_Avg_US_Power_dBmV'
            # Sync-Geschwindigkeit
            header += ';FB_Sync_DS_Kbps;FB_Sync_US_Kbps'
            # Verbindung
            header += ';FB_Connection_Time'
            # Top Problem-Kanal
            header += ';FB_Top_Problem_Channel;FB_Top_Problem_Errors\n'
            
            # Erweitere Daten
            if len(lines) > 1:
                data_line = lines[1].strip()
                
                # Fehlerstatistik
                data_line += f';{fritzbox_data.get("total_non_corr_errors", 0)}'
                data_line += f';{fritzbox_data.get("total_corr_errors", 0)}'
                
                # Kanalzählung
                data_line += f';{fritzbox_data.get("docsis31_ds_channels", 0)}'
                data_line += f';{fritzbox_data.get("docsis30_ds_channels", 0)}'
                data_line += f';{fritzbox_data.get("docsis31_us_channels", 0)}'
                data_line += f';{fritzbox_data.get("docsis30_us_channels", 0)}'
                
                # Signalpegel
                data_line += f';{fritzbox_data.get("avg_ds_power_level", 0):.1f}'
                data_line += f';{fritzbox_data.get("min_ds_power_level", 0):.1f}'
                data_line += f';{fritzbox_data.get("max_ds_power_level", 0):.1f}'
                data_line += f';{fritzbox_data.get("avg_us_power_level", 0):.1f}'
                
                # Sync-Geschwindigkeit
                data_line += f';{fritzbox_data.get("sync_ds_speed_kbps", 0)}'
                data_line += f';{fritzbox_data.get("sync_us_speed_kbps", 0)}'
                
                # Verbindung
                data_line += f';{fritzbox_data.get("connection_time", "")}'
                
                # Top Problem-Kanal
                problem_channels = fritzbox_data.get('problem_channels', [])
                if problem_channels:
                    top_ch = problem_channels[0]
                    data_line += f';{top_ch["channel_id"]}'
                    data_line += f';{top_ch["non_corr_errors"]}'
                else:
                    data_line += ';0;0'
                data_line += '\n'
                
                # Schreibe erweiterte CSV
                with open(latest_csv, 'w', encoding='utf-8') as file:
                    file.write(header)
                    file.write(data_line)
                
                # Erstelle detaillierte DOCSIS-CSV mit allen Kanal-Infos
                detail_csv = latest_csv.replace('.csv', '_docsis.csv')
                raw_all = fritzbox_data.get('raw_all_data', {})
                parsed = raw_all.get('parsed', {}) if raw_all else {}
                
                with open(detail_csv, 'w', encoding='utf-8') as file:
                    file.write("Timestamp;Direction;DOCSIS;Channel_ID;Frequency;Modulation;Power_Level;MER_MSE_dB;Non_Corr_Errors;Corr_Errors\n")
                    
                    # DOCSIS 3.1 Downstream
                    for ch in parsed.get('downstream', {}).get('docsis31', []):
                        file.write(f"{fritzbox_data['timestamp']};Downstream;3.1")
                        file.write(f";{ch.get('channel_id', '')}")
                        file.write(f";{ch.get('frequency', '')}")
                        file.write(f";{ch.get('modulation', '')}")
                        file.write(f";{ch.get('power_level', '')}")
                        file.write(f";{ch.get('mer', 0)}")
                        file.write(f";{ch.get('non_corr_errors', 0)}")
                        file.write(f";0\n")
                    
                    # DOCSIS 3.0 Downstream
                    for ch in parsed.get('downstream', {}).get('docsis30', []):
                        file.write(f"{fritzbox_data['timestamp']};Downstream;3.0")
                        file.write(f";{ch.get('channel_id', '')}")
                        file.write(f";{ch.get('frequency', '')}")
                        file.write(f";{ch.get('modulation', '')}")
                        file.write(f";{ch.get('power_level', '')}")
                        file.write(f";{ch.get('mse', 0)}")
                        file.write(f";{ch.get('non_corr_errors', 0)}")
                        file.write(f";{ch.get('corr_errors', 0)}\n")
                    
                    # Upstream
                    for ch in parsed.get('upstream', {}).get('docsis31', []):
                        file.write(f"{fritzbox_data['timestamp']};Upstream;3.1")
                        file.write(f";{ch.get('channel_id', '')}")
                        file.write(f";{ch.get('frequency', '')}")
                        file.write(f";{ch.get('modulation', '')}")
                        file.write(f";{ch.get('power_level', '')}")
                        file.write(f";0;0;0\n")
                    
                    for ch in parsed.get('upstream', {}).get('docsis30', []):
                        file.write(f"{fritzbox_data['timestamp']};Upstream;3.0")
                        file.write(f";{ch.get('channel_id', '')}")
                        file.write(f";{ch.get('frequency', '')}")
                        file.write(f";{ch.get('modulation', '')}")
                        file.write(f";{ch.get('power_level', '')}")
                        file.write(f";0;0;0\n")
                
                print(f"📋 DOCSIS-Details: {os.path.basename(detail_csv)}", flush=True)
                
                # Speichere ALLE Rohdaten als JSON für spätere Analyse
                json_file = latest_csv.replace('.csv', '_fritzbox_full.json')
                with open(json_file, 'w', encoding='utf-8') as f:
                    # Entferne das raw_all_data um Rekursion zu vermeiden
                    save_data = {k: v for k, v in fritzbox_data.items() if k != 'raw_all_data'}
                    save_data['raw_docsis'] = raw_all.get('docsis')
                    save_data['raw_cable_overview'] = raw_all.get('cable_overview')
                    save_data['raw_connection'] = raw_all.get('connection')
                    save_data['raw_traffic'] = raw_all.get('traffic')
                    json.dump(save_data, f, indent=2, default=str)
                print(f"📋 JSON-Rohdaten: {os.path.basename(json_file)}", flush=True)
        
        # Zeige Ergebnisse
        print("\n" + "=" * 50)
        print("📊 MESSERGEBNISSE:")
        print("=" * 50)
        print(f"  📥 Download: {download} Mbit/s")
        print(f"  📤 Upload:   {upload} Mbit/s")
        print(f"  ⚡ Ping:     {ping} ms")
        
        if fritzbox_data:
            print("\n📡 FritzBox DOCSIS-Status:")
            print(f"  📊 DOCSIS 3.1: {fritzbox_data.get('docsis31_ds_channels', 0)} DS / {fritzbox_data.get('docsis31_us_channels', 0)} US Kanäle")
            print(f"  📊 DOCSIS 3.0: {fritzbox_data.get('docsis30_ds_channels', 0)} DS / {fritzbox_data.get('docsis30_us_channels', 0)} US Kanäle")
            print(f"  🔴 Nicht korrigierbare Fehler: {fritzbox_data.get('total_non_corr_errors', 0):,}")
            print(f"  🟡 Korrigierte Fehler: {fritzbox_data.get('total_corr_errors', 0):,}")
            
            # Signalpegel
            if fritzbox_data.get('avg_ds_power_level'):
                print(f"  📶 DS Power: {fritzbox_data.get('min_ds_power_level', 0):.1f} - {fritzbox_data.get('max_ds_power_level', 0):.1f} dBmV (Ø {fritzbox_data.get('avg_ds_power_level', 0):.1f})")
            if fritzbox_data.get('avg_us_power_level'):
                print(f"  📶 US Power: Ø {fritzbox_data.get('avg_us_power_level', 0):.1f} dBmV")
            
            # Sync-Geschwindigkeit
            if fritzbox_data.get('sync_ds_speed_kbps'):
                print(f"  🚀 Sync: {fritzbox_data.get('sync_ds_speed_kbps', 0)/1000:.0f} Mbit/s DS / {fritzbox_data.get('sync_us_speed_kbps', 0)/1000:.0f} Mbit/s US")
            
            # Verbindungszeit
            if fritzbox_data.get('connection_time'):
                print(f"  ⏱️  Verbindung: {fritzbox_data.get('connection_time')}")
            
            # Zeige Problem-Kanäle
            problem_channels = fritzbox_data.get('problem_channels', [])
            if problem_channels:
                print(f"\n  🚨 TOP PROBLEM-KANÄLE:")
                for ch in problem_channels[:5]:  # Top 5
                    severity = "🔴🔴🔴" if ch['non_corr_errors'] > 1_000_000 else "🔴"
                    print(f"     {severity} Kanal {ch['channel_id']:2d}: {ch['non_corr_errors']:>15,} Fehler")
        
        print("=" * 50)
        print(f"\n💾 CSV gespeichert: {os.path.basename(latest_csv)}")
        
        # Screenshot nur von der Breitbandmessung-Ergebnisseite (optional)
        if SAVE_SCREENSHOTS:
            now = datetime.now()
            screenshot_name = f"Breitbandmessung_{now.strftime('%d_%m_%Y_%H_%M_%S')}.png"
            screenshot_path = os.path.join(EXPORT_PATH, screenshot_name)
            browser.save_screenshot(screenshot_path)
            print(f"📸 Screenshot: {screenshot_name}")
        
        # FritzBox-Screenshots DEAKTIVIERT - Daten werden jetzt direkt via API geholt
        # und als JSON/CSV gespeichert (viel besser für Analyse!)
        
        print("\n✅ Fertig!\n")
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        # Fehler-Screenshot
        if SAVE_SCREENSHOTS:
            now = datetime.now()
            error_screenshot = f"ERROR_{now.strftime('%d_%m_%Y_%H_%M_%S')}.png"
            browser.save_screenshot(os.path.join(EXPORT_PATH, error_screenshot))
            print(f"📸 Fehler-Screenshot: {error_screenshot}")
        raise
    finally:
        browser.quit()
        cleanup_firefox()


if __name__ == "__main__":
    ensure_export_directory()
    run_speedtest()