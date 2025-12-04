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

# Lade Konfiguration
config = configparser.ConfigParser()
config.read("/usr/src/app/config/config.ini")

# Einstellungen aus Config
EXPORT_PATH = config.get("Settings", "export_path", fallback="/export")
SLEEPTIME = config.getint("Settings", "wait_time", fallback=10)
SAVE_SCREENSHOTS = config.getboolean("Settings", "save_screenshots", fallback=True)

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
        
        # Zeige Ergebnisse
        print("\n" + "=" * 50)
        print("📊 MESSERGEBNISSE:")
        print("=" * 50)
        print(f"  📥 Download: {download} Mbit/s")
        print(f"  📤 Upload:   {upload} Mbit/s")
        print(f"  ⚡ Ping:     {ping} ms")
        print("=" * 50)
        print(f"\n💾 CSV gespeichert: {os.path.basename(latest_csv)}")
        
        # Screenshot (optional)
        if SAVE_SCREENSHOTS:
            now = datetime.now()
            screenshot_name = f"Breitbandmessung_{now.strftime('%d_%m_%Y_%H_%M_%S')}.png"
            screenshot_path = os.path.join(EXPORT_PATH, screenshot_name)
            browser.save_screenshot(screenshot_path)
            print(f"📸 Screenshot: {screenshot_name}")
        
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