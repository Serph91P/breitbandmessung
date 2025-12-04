#!/usr/local/bin/python3
"""
Breitbandmessung - Einfacher Speedtest mit CSV-Export
Führt automatisierte Messungen über breitbandmessung.de durch
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
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET

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
    """Liest Kabel-DOCSIS Informationen von der FritzBox aus"""
    if not FRITZBOX_ENABLED:
        return None
    
    try:
        print("\n📡 Lese FritzBox Cable-Informationen...", flush=True)
        
        # Versuche erst die JSON-API (moderne FritzBoxen)
        json_data = get_fritzbox_cable_json()
        if json_data:
            return json_data
        
        # FritzBox Cable Info über TR-064
        url = f"http://{FRITZBOX_HOST}:49000/igdupnp/control/WANCableLinkConfig1"
        
        headers = {
            'Content-Type': 'text/xml; charset="utf-8"',
            'SOAPAction': 'urn:dslforum-org:service:WANCableLinkConfig:1#GetCableInfo'
        }
        
        soap_body = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:GetCableInfo xmlns:u="urn:dslforum-org:service:WANCableLinkConfig:1" />
    </s:Body>
</s:Envelope>"""
        
        auth = None
        if FRITZBOX_USER and FRITZBOX_PASSWORD:
            auth = HTTPDigestAuth(FRITZBOX_USER, FRITZBOX_PASSWORD)
        
        response = requests.post(url, data=soap_body, headers=headers, auth=auth, timeout=10)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            def get_value(tag):
                elem = root.find(f".//{{{root.tag.split('}')[0][1:]}}}New{tag}")
                if elem is None:
                    elem = root.find(f".//New{tag}")
                return elem.text if elem is not None else "N/A"
            
            # Sammle Downstream-Kanäle
            downstream_channels = []
            upstream_channels = []
            
            # Parse Downstream Info (kann mehrere Formate haben)
            ds_info = get_value('DownstreamChannelStatus')
            if ds_info and ds_info != "N/A":
                # Parse Channel-String (meist komma-separiert)
                for line in ds_info.split('\n'):
                    if line.strip():
                        downstream_channels.append(line.strip())
            
            # Parse Upstream Info
            us_info = get_value('UpstreamChannelStatus')
            if us_info and us_info != "N/A":
                for line in us_info.split('\n'):
                    if line.strip():
                        upstream_channels.append(line.strip())
            
            cable_info = {
                'downstream_frequency': get_value('DownstreamFrequency'),
                'downstream_powerLevel': get_value('DownstreamPowerLevel'),
                'downstream_modulation': get_value('DownstreamModulation'),
                'upstream_frequency': get_value('UpstreamFrequency'),
                'upstream_powerLevel': get_value('UpstreamPowerLevel'),
                'upstream_modulation': get_value('UpstreamModulation'),
                'cable_status': get_value('CableStatus'),
                'link_status': get_value('LinkStatus'),
                'downstream_channels': downstream_channels,
                'upstream_channels': upstream_channels,
                'total_codewords': get_value('TotalCodewords'),
                'corrected_codewords': get_value('CorrectedCodewords'),
                'uncorrected_codewords': get_value('UncorrectedCodewords')
            }
            
            print("✓ FritzBox Cable-Daten gelesen", flush=True)
            print(f"  📶 Status: {cable_info['link_status']}", flush=True)
            print(f"  ⬇️  Downstream: {cable_info['downstream_frequency']} MHz", flush=True)
            print(f"  ⬆️  Upstream: {cable_info['upstream_frequency']} MHz", flush=True)
            print(f"  🔴 Nicht korrigierbar: {cable_info['uncorrected_codewords']}", flush=True)
            print(f"  � Korrigiert: {cable_info['corrected_codewords']}", flush=True)
            
            return cable_info
        else:
            print(f"⚠️  FritzBox Fehler: HTTP {response.status_code}", flush=True)
            print(f"     Tipp: Nutze FritzBox Web-Interface zum manuellen Export", flush=True)
            return None
            
    except Exception as e:
        print(f"⚠️  FritzBox API Fehler: {e}", flush=True)
        print(f"     Versuche Alternative: Web-Scraping...", flush=True)
        return get_fritzbox_cable_via_web()


def get_fritzbox_cable_json():
    """Versuche FritzBox Cable-Daten über JSON API zu holen"""
    try:
        # Moderne FritzBox JSON-Endpoints (ohne Auth für lokale Zugriffe)
        endpoints = [
            f"http://{FRITZBOX_HOST}/data.lua?page=docInfo",
            f"http://{FRITZBOX_HOST}/data.lua?page=cable",
            f"http://{FRITZBOX_HOST}/query.lua?network=docsis_state",
            f"http://{FRITZBOX_HOST}/internet/inetstat_monitor.lua?useajax=1&action=get_graphic"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code == 200:
                    # Versuche JSON zu parsen
                    try:
                        data = response.json()
                        if data and len(str(data)) > 50:  # Nicht leer
                            print(f"  ✓ JSON-Daten gefunden: {endpoint.split('/')[-1]}", flush=True)
                            
                            # Parse relevante Daten
                            cable_info = {
                                'source': 'json_api',
                                'endpoint': endpoint,
                                'raw_data': str(data)[:500],  # Erste 500 Zeichen
                                'data': data
                            }
                            
                            # Versuche Kanal-Daten zu extrahieren
                            if 'downstream' in str(data).lower():
                                print(f"  ✓ Downstream-Kanäle gefunden!", flush=True)
                            if 'upstream' in str(data).lower():
                                print(f"  ✓ Upstream-Kanäle gefunden!", flush=True)
                            
                            return cable_info
                    except:
                        pass
            except:
                continue
        
        print("  ℹ️  Keine JSON-API verfügbar", flush=True)
        return None
        
    except Exception as e:
        print(f"  ℹ️  JSON-API nicht erreichbar: {e}", flush=True)
        return None


def get_fritzbox_cable_via_web():
    """Alternative: Lese Cable-Info direkt vom FritzBox Webinterface"""
    try:
        print("  → Versuche Web-Interface Zugriff...", flush=True)
        
        # FritzBox Cable-Monitor Seite (JSON Endpoint)
        base_url = f"http://{FRITZBOX_HOST}"
        
        session = requests.Session()
        
        # Login falls nötig
        if FRITZBOX_USER and FRITZBOX_PASSWORD:
            login_url = f"{base_url}/login_sid.lua"
            # Hole Challenge
            resp = session.get(login_url, timeout=10)
            # Parse Challenge aus XML
            import hashlib
            root = ET.fromstring(resp.content)
            challenge = root.find('Challenge').text if root.find('Challenge') is not None else None
            
            if challenge:
                # MD5(challenge + "-" + MD5(password))
                md5_pass = hashlib.md5(FRITZBOX_PASSWORD.encode('utf-16le')).hexdigest()
                response_str = f"{challenge}-{md5_pass}"
                response_hash = hashlib.md5(response_str.encode()).hexdigest()
                
                # Login
                login_data = {
                    'username': FRITZBOX_USER,
                    'response': f"{challenge}-{response_hash}"
                }
                session.post(login_url, data=login_data, timeout=10)
        
        # Hole Cable-Daten (spezielle URL für Cable-Modems)
        cable_url = f"{base_url}/cgi-bin/webcm"
        params = {
            'getpage': '../html/de/menus/menu2.html',
            'var:lang': 'de',
            'var:pagename': 'docinfo',
            'var:menu': 'home'
        }
        
        resp = session.get(cable_url, params=params, timeout=10)
        
        if resp.status_code == 200:
            # Parse HTML für Cable-Infos
            text = resp.text
            
            # Einfaches Parsing (besser wäre BeautifulSoup, aber wir halten es minimal)
            channels_info = {
                'downstream': [],
                'upstream': [],
                'raw_html': text[:500]  # Erste 500 Zeichen als Debug
            }
            
            print("✓ FritzBox Web-Daten empfangen", flush=True)
            return channels_info
        
        print("⚠️  Web-Interface nicht erreichbar", flush=True)
        return None
        
    except Exception as e:
        print(f"⚠️  Web-Zugriff Fehler: {e}", flush=True)
        return None


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
        
        # Erweitere CSV mit FritzBox Cable-Daten
        if fritzbox_data:
            # Lese komplette CSV
            with open(latest_csv, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Erweitere Header
            header = lines[0].strip()
            header += ';FB_Cable_Status;FB_Link_Status;FB_DS_Freq;FB_DS_Power;FB_DS_Modulation'
            header += ';FB_US_Freq;FB_US_Power;FB_US_Modulation'
            header += ';FB_Total_Codewords;FB_Corrected_Errors;FB_Uncorrected_Errors'
            header += ';FB_DS_Channels;FB_US_Channels\n'
            
            # Erweitere Daten
            if len(lines) > 1:
                data_line = lines[1].strip()
                data_line += f';{fritzbox_data.get("cable_status", "N/A")}'
                data_line += f';{fritzbox_data.get("link_status", "N/A")}'
                data_line += f';{fritzbox_data.get("downstream_frequency", "N/A")}'
                data_line += f';{fritzbox_data.get("downstream_powerLevel", "N/A")}'
                data_line += f';{fritzbox_data.get("downstream_modulation", "N/A")}'
                data_line += f';{fritzbox_data.get("upstream_frequency", "N/A")}'
                data_line += f';{fritzbox_data.get("upstream_powerLevel", "N/A")}'
                data_line += f';{fritzbox_data.get("upstream_modulation", "N/A")}'
                data_line += f';{fritzbox_data.get("total_codewords", "N/A")}'
                data_line += f';{fritzbox_data.get("corrected_codewords", "0")}'
                data_line += f';{fritzbox_data.get("uncorrected_codewords", "0")}'
                
                # Channel-Infos als String (Anzahl der Kanäle)
                ds_ch_count = len(fritzbox_data.get("downstream_channels", []))
                us_ch_count = len(fritzbox_data.get("upstream_channels", []))
                data_line += f';{ds_ch_count};{us_ch_count}\n'
                
                # Schreibe erweiterte CSV
                with open(latest_csv, 'w', encoding='utf-8') as file:
                    file.write(header)
                    file.write(data_line)
                
                # Erstelle zusätzliche Detail-CSV mit allen Kanal-Infos
                detail_csv = latest_csv.replace('.csv', '_channels.csv')
                with open(detail_csv, 'w', encoding='utf-8') as file:
                    file.write("Channel_Direction;Channel_ID;Info\n")
                    for idx, ch in enumerate(fritzbox_data.get("downstream_channels", [])):
                        file.write(f"Downstream;{idx+1};{ch}\n")
                    for idx, ch in enumerate(fritzbox_data.get("upstream_channels", [])):
                        file.write(f"Upstream;{idx+1};{ch}\n")
                
                print(f"📋 Channel-Details: {os.path.basename(detail_csv)}", flush=True)
        
        # Zeige Ergebnisse
        print("\n" + "=" * 50)
        print("📊 MESSERGEBNISSE:")
        print("=" * 50)
        print(f"  📥 Download: {download} Mbit/s")
        print(f"  📤 Upload:   {upload} Mbit/s")
        print(f"  ⚡ Ping:     {ping} ms")
        
        if fritzbox_data:
            print("\n📡 FritzBox Cable-Info:")
            print(f"  📶 Link: {fritzbox_data.get('link_status', 'N/A')}")
            print(f"  ⬇️  Downstream: {fritzbox_data.get('downstream_frequency', 'N/A')} MHz ({fritzbox_data.get('downstream_modulation', 'N/A')})")
            print(f"     Power: {fritzbox_data.get('downstream_powerLevel', 'N/A')} dBmV")
            print(f"  ⬆️  Upstream: {fritzbox_data.get('upstream_frequency', 'N/A')} MHz ({fritzbox_data.get('upstream_modulation', 'N/A')})")
            print(f"     Power: {fritzbox_data.get('upstream_powerLevel', 'N/A')} dBmV")
            print(f"  🔴 Nicht korrigierbare Fehler: {fritzbox_data.get('uncorrected_codewords', '0')}")
            print(f"  🟡 Korrigierte Fehler: {fritzbox_data.get('corrected_codewords', '0')}")
            ds_count = len(fritzbox_data.get('downstream_channels', []))
            us_count = len(fritzbox_data.get('upstream_channels', []))
            print(f"  📊 Kanäle: {ds_count} Downstream, {us_count} Upstream")
        
        print("=" * 50)
        print(f"\n💾 CSV gespeichert: {os.path.basename(latest_csv)}")
        
        # Screenshot (optional)
        if SAVE_SCREENSHOTS:
            now = datetime.now()
            screenshot_name = f"Breitbandmessung_{now.strftime('%d_%m_%Y_%H_%M_%S')}.png"
            screenshot_path = os.path.join(EXPORT_PATH, screenshot_name)
            browser.save_screenshot(screenshot_path)
            print(f"📸 Screenshot: {screenshot_name}")
        
        # FritzBox Cable-Seite Screenshot (falls aktiviert)
        if FRITZBOX_ENABLED and FRITZBOX_SCREENSHOT:
            print("\n📡 Erstelle FritzBox Cable Screenshots...")
            try:
                now = datetime.now()
                
                # Login in FritzBox (falls Passwort gesetzt)
                if FRITZBOX_PASSWORD:
                    print(f"  🔐 Login in FritzBox...")
                    browser.get(f"http://{FRITZBOX_HOST}")
                    time.sleep(2)
                    
                    try:
                        # Passwort-Feld finden und ausfüllen (Username ist Dropdown, brauchen wir nicht)
                        password_field = browser.find_element(By.ID, "uiPass")
                        password_field.clear()
                        password_field.send_keys(FRITZBOX_PASSWORD)
                        
                        # Login-Button klicken
                        login_button = browser.find_element(By.ID, "submitLoginBtn")
                        login_button.click()
                        
                        # Warte bis Login durch ist
                        time.sleep(2)
                        print(f"  ✓ Login erfolgreich")
                    except Exception as e:
                        print(f"  ⚠️  Login fehlgeschlagen: {e}")
                        print(f"  → Tipp: Prüfe Passwort in config.ini")
                        print(f"  → Oder FritzBox ist schon eingeloggt (Session aktiv)")
                
                # Screenshot-URLs - ALLE Cable-Seiten!
                cable_pages = [
                    ("cable_overview", f"http://{FRITZBOX_HOST}/#/cable"),
                    ("cable_channels", f"http://{FRITZBOX_HOST}/#/cable/channels"),
                    ("cable_spectrum", f"http://{FRITZBOX_HOST}/#/cable/spectrum"),
                    ("cable_utilization", f"http://{FRITZBOX_HOST}/#/cable/utilization")
                ]
                
                screenshot_count = 0
                for page_name, url in cable_pages:
                    try:
                        print(f"  → {page_name}: {url}")
                        browser.get(url)
                        time.sleep(5)  # Warte auf moderne UI
                        
                        # Screenshot
                        screenshot_name = f"FritzBox_{page_name}_{now.strftime('%d_%m_%Y_%H_%M_%S')}.png"
                        screenshot_path = os.path.join(EXPORT_PATH, screenshot_name)
                        browser.save_screenshot(screenshot_path)
                        print(f"  ✓ {screenshot_name}")
                        screenshot_count += 1
                    except Exception as e:
                        print(f"  ⚠️  {page_name} Fehler: {e}")
                
                if screenshot_count > 0:
                    print(f"\n  📸 {screenshot_count} FritzBox Screenshots erstellt!")
                    print(f"  📊 Zeigt ALLE DOCSIS-Daten: Kanäle, Spektrum, Auslastung")
                else:
                    print(f"\n  ⚠️  Keine Screenshots erstellt - prüfe FritzBox-Zugriff")
                
            except Exception as e:
                print(f"⚠️  FritzBox Screenshot Fehler: {e}")
                print(f"     Tipp: Setze FritzBox-Passwort in config.ini:")
                print(f"     [FritzBox]")
                print(f"     password = dein-passwort")
        
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