#!/usr/bin/env python3
"""
FritzBox 6690 Cable - DOCSIS Kanal-Daten Auslesen

Standalone-Modul zum Auslesen der FritzBox DOCSIS-Daten.
Kann direkt ausgeführt oder als Modul importiert werden.

Verwendung standalone:
    python fritzbox_cable.py                    # Einmal ausführen
    python fritzbox_cable.py --watch            # Alle 30 Min wiederholen
    python fritzbox_cable.py --json             # Nur JSON ausgeben
    
Als Modul:
    from fritzbox_cable import FritzBoxCable
    fb = FritzBoxCable("http://fritz.box", "user", "password")
    data = fb.get_all_cable_data()  # Alle verfügbaren Daten
"""

import hashlib
import requests
import json
import os
import sys
import time
import csv
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

# ============================================================================
# KONFIGURATION (wird überschrieben wenn als Modul verwendet)
# ============================================================================

DEFAULT_URL = os.environ.get("FRITZBOX_HOST", "http://fritz.box")
DEFAULT_USER = os.environ.get("FRITZBOX_USER", "")
DEFAULT_PASSWORD = os.environ.get("FRITZBOX_PASSWORD", "")


class FritzBoxCable:
    """
    FritzBox Cable/DOCSIS API Client.
    
    Unterstützt die interne JSON-API der FritzBox für Kabel-Router.
    """
    
    def __init__(self, url: str = None, user: str = None, password: str = None):
        self.url = (url or DEFAULT_URL).rstrip('/')
        if not self.url.startswith('http'):
            self.url = f"http://{self.url}"
        self.user = user or DEFAULT_USER
        self.password = password or DEFAULT_PASSWORD
        self.sid = None
        self.session = requests.Session()
        self.session.timeout = 10
    
    def login(self) -> bool:
        """
        Meldet sich an der FritzBox an und holt eine Session-ID.
        Verwendet Challenge-Response mit MD5 (FritzBox Standard).
        """
        login_url = f"{self.url}/login_sid.lua"
        
        try:
            # Schritt 1: Challenge holen
            response = self.session.get(login_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Verbindungsfehler zu {self.url}: {e}")
            return False
        
        try:
            root = ET.fromstring(response.text)
            challenge = root.find('Challenge').text
            current_sid = root.find('SID').text
        except Exception as e:
            print(f"❌ Fehler beim Parsen der Login-Antwort: {e}")
            return False
        
        # Prüfe ob bereits eine gültige Session existiert
        if current_sid and current_sid != "0000000000000000":
            self.sid = current_sid
            return True
        
        # Schritt 2: Challenge-Response berechnen
        # FritzBox erwartet: challenge-md5(challenge-password) 
        # Encoding: UTF-16LE für den MD5-Hash
        response_str = f"{challenge}-{self.password}"
        
        # UTF-16LE encoding für MD5 (FritzBox Spezifikation)
        response_bytes = response_str.encode('utf-16-le')
        response_hash = hashlib.md5(response_bytes).hexdigest()
        response_value = f"{challenge}-{response_hash}"
        
        # Schritt 3: Login mit Username und Response
        login_data = {'response': response_value}
        if self.user:
            login_data['username'] = self.user
        
        try:
            response = self.session.post(login_url, data=login_data, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            self.sid = root.find('SID').text
        except Exception as e:
            print(f"❌ Login-Fehler: {e}")
            return False
        
        if not self.sid or self.sid == "0000000000000000":
            # Prüfe ob BlockTime gesetzt ist
            try:
                block_time = root.find('BlockTime').text
                if block_time and int(block_time) > 0:
                    print(f"❌ Login blockiert für {block_time} Sekunden (zu viele Fehlversuche)")
                    return False
            except:
                pass
            print("❌ Login fehlgeschlagen - falsches Passwort oder Benutzername?")
            return False
        
        return True
    
    def _get_page(self, page: str) -> dict | None:
        """Ruft eine FritzBox data.lua Seite ab."""
        if not self.sid:
            if not self.login():
                return None
        
        data_url = f"{self.url}/data.lua"
        params = {'sid': self.sid, 'page': page}
        
        try:
            response = self.session.post(data_url, data=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Fehler beim Abrufen von '{page}': {e}")
            return None
        except json.JSONDecodeError:
            print(f"❌ Ungültige JSON-Antwort von '{page}'")
            return None
    
    def get_docsis_data(self) -> dict | None:
        """
        Ruft die DOCSIS-Kanaldaten ab.
        
        Returns:
            dict mit Struktur:
            {
                'timestamp': '...',
                'channelDs': {'docsis31': [...], 'docsis30': [...]},
                'channelUs': {'docsis31': [...], 'docsis30': [...]},
            }
        """
        raw = self._get_page('docInfo')
        if not raw or 'data' not in raw:
            return None
        return raw['data']
    
    def get_cable_overview(self) -> dict | None:
        """Ruft die Kabel-Übersicht ab (Geschwindigkeit, Verbindungsstatus)."""
        raw = self._get_page('docOv')
        if not raw or 'data' not in raw:
            return None
        return raw['data']
    
    def get_connection_info(self) -> dict | None:
        """
        Ruft Internet-Verbindungsinformationen ab.
        Enthält: IP, Verbindungsdauer, Provider-Daten
        """
        raw = self._get_page('netMoni')
        if not raw or 'data' not in raw:
            return None
        return raw['data']
    
    def get_traffic_data(self) -> dict | None:
        """
        Ruft Traffic/Auslastungsdaten ab.
        Enthält: Aktuelle Up/Down Geschwindigkeit, Historie
        """
        raw = self._get_page('netCnt')
        if not raw or 'data' not in raw:
            return None
        return raw['data']
    
    def get_energy_data(self) -> dict | None:
        """Ruft Energie/System-Status ab."""
        raw = self._get_page('energy')
        if not raw or 'data' not in raw:
            return None
        return raw['data']
    
    def get_all_cable_data(self) -> dict:
        """
        Ruft ALLE verfügbaren Kabel-Daten ab und kombiniert sie.
        Dies ist die Hauptmethode für maximale Datensammlung.
        
        Returns:
            dict mit allen Kabel- und Verbindungsdaten
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'docsis': None,
            'cable_overview': None,
            'connection': None,
            'traffic': None,
            'energy': None,
            'parsed': None
        }
        
        # DOCSIS Kanaldaten (wichtigste Daten)
        result['docsis'] = self.get_docsis_data()
        
        # Kabel-Übersicht (Geschwindigkeit, Status)
        result['cable_overview'] = self.get_cable_overview()
        
        # Verbindungsinfo
        result['connection'] = self.get_connection_info()
        
        # Traffic-Daten
        result['traffic'] = self.get_traffic_data()
        
        # Energie/System
        result['energy'] = self.get_energy_data()
        
        # Geparste DOCSIS-Daten
        result['parsed'] = self.get_parsed_docsis_data()
        
        result['success'] = result['docsis'] is not None
        
        return result
    
    def get_parsed_docsis_data(self) -> dict:
        """
        Ruft DOCSIS-Daten ab und parst sie in ein übersichtliches Format.
        
        Returns:
            dict mit Statistiken und Fehlerübersicht
        """
        raw_data = self.get_docsis_data()
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'downstream': {
                'docsis31': [],
                'docsis30': []
            },
            'upstream': {
                'docsis31': [],
                'docsis30': []
            },
            'summary': {
                'total_non_corr_errors': 0,
                'total_corr_errors': 0,
                'problem_channels': []
            }
        }
        
        if not raw_data:
            return result
        
        result['success'] = True
        
        # Downstream Kanäle parsen
        if 'channelDs' in raw_data:
            # DOCSIS 3.1
            for ch in raw_data['channelDs'].get('docsis31', []):
                parsed = {
                    'channel_id': ch.get('channelID'),
                    'frequency': ch.get('frequency'),
                    'modulation': ch.get('modulation'),
                    'power_level': float(ch.get('powerLevel', 0)),
                    'mer': float(ch.get('mer', 0)),
                    'non_corr_errors': int(ch.get('nonCorrErrors', 0)),
                    'plc': ch.get('plc'),
                    'fft': ch.get('fft')
                }
                result['downstream']['docsis31'].append(parsed)
                result['summary']['total_non_corr_errors'] += parsed['non_corr_errors']
            
            # DOCSIS 3.0
            for ch in raw_data['channelDs'].get('docsis30', []):
                parsed = {
                    'channel_id': ch.get('channelID'),
                    'frequency': ch.get('frequency'),
                    'modulation': ch.get('modulation'),
                    'power_level': float(ch.get('powerLevel', 0)),
                    'mse': float(ch.get('mse', 0)),
                    'latency': float(ch.get('latency', 0)),
                    'corr_errors': int(ch.get('corrErrors', 0)),
                    'non_corr_errors': int(ch.get('nonCorrErrors', 0))
                }
                result['downstream']['docsis30'].append(parsed)
                result['summary']['total_non_corr_errors'] += parsed['non_corr_errors']
                result['summary']['total_corr_errors'] += parsed['corr_errors']
        
        # Upstream Kanäle parsen
        if 'channelUs' in raw_data:
            for ch in raw_data['channelUs'].get('docsis31', []):
                result['upstream']['docsis31'].append({
                    'channel_id': ch.get('channelID'),
                    'frequency': ch.get('frequency'),
                    'modulation': ch.get('modulation'),
                    'power_level': float(ch.get('powerLevel', 0)),
                    'fft': ch.get('fft'),
                    'active_subcarriers': ch.get('activesub')
                })
            
            for ch in raw_data['channelUs'].get('docsis30', []):
                result['upstream']['docsis30'].append({
                    'channel_id': ch.get('channelID'),
                    'frequency': ch.get('frequency'),
                    'modulation': ch.get('modulation'),
                    'power_level': float(ch.get('powerLevel', 0)),
                    'multiplex': ch.get('multiplex')
                })
        
        # Problem-Kanäle identifizieren
        all_ds = result['downstream']['docsis31'] + result['downstream']['docsis30']
        for ch in all_ds:
            if ch.get('non_corr_errors', 0) > 0:
                result['summary']['problem_channels'].append({
                    'channel_id': ch['channel_id'],
                    'frequency': ch['frequency'],
                    'non_corr_errors': ch['non_corr_errors']
                })
        
        # Nach Fehlern sortieren
        result['summary']['problem_channels'].sort(
            key=lambda x: x['non_corr_errors'], reverse=True
        )
        
        return result
    
    def logout(self):
        """Meldet sich von der FritzBox ab."""
        if self.sid:
            try:
                self.session.get(
                    f"{self.url}/login_sid.lua",
                    params={'logout': '1', 'sid': self.sid},
                    timeout=5
                )
            except:
                pass
            self.sid = None
    
    def __enter__(self):
        self.login()
        return self
    
    def __exit__(self, *args):
        self.logout()


def save_to_csv(data: dict, filepath: str):
    """Speichert Fehlerdaten in CSV-Datei."""
    fieldnames = ['timestamp', 'total_non_corr_errors', 'total_corr_errors',
                  'ch31_errors', 'ch28_errors', 'ch5_errors']
    
    # Fehler für spezifische Kanäle
    ch_errors = {31: 0, 28: 0, 5: 0}
    for ch in data['downstream']['docsis31']:
        if ch['channel_id'] in ch_errors:
            ch_errors[ch['channel_id']] = ch['non_corr_errors']
    for ch in data['downstream']['docsis30']:
        if ch['channel_id'] in ch_errors:
            ch_errors[ch['channel_id']] = ch['non_corr_errors']
    
    row = {
        'timestamp': data['timestamp'],
        'total_non_corr_errors': data['summary']['total_non_corr_errors'],
        'total_corr_errors': data['summary']['total_corr_errors'],
        'ch31_errors': ch_errors[31],
        'ch28_errors': ch_errors[28],
        'ch5_errors': ch_errors[5]
    }
    
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def print_summary(data: dict):
    """Gibt eine übersichtliche Zusammenfassung aus."""
    print("\n" + "=" * 70)
    print("📡 FRITZBOX DOCSIS FEHLERSTATISTIK")
    print("=" * 70)
    print(f"⏰ Zeitpunkt: {data['timestamp']}")
    
    total_non_corr = data['summary']['total_non_corr_errors']
    total_corr = data['summary']['total_corr_errors']
    
    print(f"\n📊 GESAMT:")
    print(f"   🔴 Nicht korrigierbare Fehler: {total_non_corr:,}")
    print(f"   🟡 Korrigierbare Fehler:       {total_corr:,}")
    
    if data['summary']['problem_channels']:
        print(f"\n🚨 PROBLEM-KANÄLE:")
        print("-" * 70)
        for ch in data['summary']['problem_channels']:
            severity = "🔴🔴🔴" if ch['non_corr_errors'] > 1_000_000 else "🔴" if ch['non_corr_errors'] > 1000 else "🟠"
            print(f"   {severity} Kanal {ch['channel_id']:2d} ({ch['frequency']} MHz): "
                  f"{ch['non_corr_errors']:>15,} Fehler")
    else:
        print(f"\n✅ Keine nicht korrigierbaren Fehler!")
    
    print("\n" + "=" * 70)


def main():
    """Hauptfunktion für Standalone-Ausführung."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FritzBox DOCSIS Daten auslesen')
    parser.add_argument('--host', default=DEFAULT_URL, help='FritzBox URL')
    parser.add_argument('--user', default=DEFAULT_USER, help='Benutzername')
    parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Passwort')
    parser.add_argument('--json', action='store_true', help='Nur JSON ausgeben')
    parser.add_argument('--watch', action='store_true', help='Alle 30 Min wiederholen')
    parser.add_argument('--output', help='CSV-Datei für Historie')
    args = parser.parse_args()
    
    if not args.password:
        print("❌ Kein Passwort angegeben!")
        print("   Nutze --password oder setze FRITZBOX_PASSWORD Umgebungsvariable")
        return 1
    
    output_file = args.output or 'fritzbox_fehler_historie.csv'
    
    while True:
        with FritzBoxCable(args.host, args.user, args.password) as fb:
            data = fb.get_parsed_docsis_data()
            
            if not data['success']:
                print("❌ Konnte keine Daten abrufen!")
                return 1
            
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print_summary(data)
                save_to_csv(data, output_file)
                print(f"💾 Gespeichert: {output_file}")
        
        if not args.watch:
            break
        
        print(f"\n⏳ Nächste Abfrage in 30 Minuten...")
        try:
            time.sleep(30 * 60)
        except KeyboardInterrupt:
            print("\n👋 Beendet.")
            break
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
