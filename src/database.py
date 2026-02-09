#!/usr/bin/env python3
"""
SQLite Datenbank-Modul für Breitbandmessung.
Speichert Messergebnisse und DOCSIS-Daten.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "/export/measurements.db")


def get_db_path():
    return DB_PATH


@contextmanager
def get_connection(db_path=None):
    """Context-Manager für DB-Verbindungen"""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    """Erstellt die Tabellen falls nicht vorhanden"""
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT UNIQUE,
                datetime TEXT NOT NULL,
                date TEXT,
                time TEXT,
                download_mbps REAL,
                upload_mbps REAL,
                ping_ms REAL,
                version TEXT,
                os TEXT,
                browser TEXT,
                
                -- FritzBox DOCSIS Zusammenfassung
                fb_non_corr_errors INTEGER,
                fb_corr_errors INTEGER,
                fb_docsis31_ds INTEGER,
                fb_docsis30_ds INTEGER,
                fb_docsis31_us INTEGER,
                fb_docsis30_us INTEGER,
                fb_avg_ds_power REAL,
                fb_min_ds_power REAL,
                fb_max_ds_power REAL,
                fb_avg_us_power REAL,
                fb_sync_ds_kbps INTEGER,
                fb_sync_us_kbps INTEGER,
                fb_connection_time TEXT,
                fb_top_problem_channel INTEGER,
                fb_top_problem_errors INTEGER,
                
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE INDEX IF NOT EXISTS idx_measurements_datetime 
                ON measurements(datetime);
            CREATE INDEX IF NOT EXISTS idx_measurements_date 
                ON measurements(date);
            
            CREATE TABLE IF NOT EXISTS docsis_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER,
                timestamp TEXT,
                direction TEXT,
                docsis_version TEXT,
                channel_id INTEGER,
                frequency TEXT,
                modulation TEXT,
                power_level REAL,
                mer_mse_db REAL,
                non_corr_errors INTEGER,
                corr_errors INTEGER,
                
                FOREIGN KEY (measurement_id) REFERENCES measurements(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_docsis_measurement 
                ON docsis_channels(measurement_id);
        """)


def insert_measurement(data, db_path=None):
    """
    Fügt eine Messung in die DB ein.
    
    data: dict mit Keys wie 'test_id', 'download_mbps', etc.
    Returns: ID der eingefügten Zeile oder None bei Duplikat
    """
    with get_connection(db_path) as conn:
        try:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO measurements (
                    test_id, datetime, date, time,
                    download_mbps, upload_mbps, ping_ms,
                    version, os, browser,
                    fb_non_corr_errors, fb_corr_errors,
                    fb_docsis31_ds, fb_docsis30_ds, fb_docsis31_us, fb_docsis30_us,
                    fb_avg_ds_power, fb_min_ds_power, fb_max_ds_power, fb_avg_us_power,
                    fb_sync_ds_kbps, fb_sync_us_kbps, fb_connection_time,
                    fb_top_problem_channel, fb_top_problem_errors
                ) VALUES (
                    :test_id, :datetime, :date, :time,
                    :download_mbps, :upload_mbps, :ping_ms,
                    :version, :os, :browser,
                    :fb_non_corr_errors, :fb_corr_errors,
                    :fb_docsis31_ds, :fb_docsis30_ds, :fb_docsis31_us, :fb_docsis30_us,
                    :fb_avg_ds_power, :fb_min_ds_power, :fb_max_ds_power, :fb_avg_us_power,
                    :fb_sync_ds_kbps, :fb_sync_us_kbps, :fb_connection_time,
                    :fb_top_problem_channel, :fb_top_problem_errors
                )
            """, {
                'test_id': data.get('test_id', ''),
                'datetime': data.get('datetime', ''),
                'date': data.get('date', ''),
                'time': data.get('time', ''),
                'download_mbps': data.get('download_mbps'),
                'upload_mbps': data.get('upload_mbps'),
                'ping_ms': data.get('ping_ms'),
                'version': data.get('version', ''),
                'os': data.get('os', ''),
                'browser': data.get('browser', ''),
                'fb_non_corr_errors': data.get('fb_non_corr_errors'),
                'fb_corr_errors': data.get('fb_corr_errors'),
                'fb_docsis31_ds': data.get('fb_docsis31_ds'),
                'fb_docsis30_ds': data.get('fb_docsis30_ds'),
                'fb_docsis31_us': data.get('fb_docsis31_us'),
                'fb_docsis30_us': data.get('fb_docsis30_us'),
                'fb_avg_ds_power': data.get('fb_avg_ds_power'),
                'fb_min_ds_power': data.get('fb_min_ds_power'),
                'fb_max_ds_power': data.get('fb_max_ds_power'),
                'fb_avg_us_power': data.get('fb_avg_us_power'),
                'fb_sync_ds_kbps': data.get('fb_sync_ds_kbps'),
                'fb_sync_us_kbps': data.get('fb_sync_us_kbps'),
                'fb_connection_time': data.get('fb_connection_time', ''),
                'fb_top_problem_channel': data.get('fb_top_problem_channel'),
                'fb_top_problem_errors': data.get('fb_top_problem_errors'),
            })
            
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None  # Duplikat
        except sqlite3.Error as e:
            print(f"⚠️ DB-Fehler: {e}")
            return None


def insert_docsis_channels(measurement_id, channels, timestamp, db_path=None):
    """Fügt DOCSIS-Kanaldaten ein"""
    if not channels or not measurement_id:
        return
    
    with get_connection(db_path) as conn:
        for ch in channels:
            conn.execute("""
                INSERT INTO docsis_channels (
                    measurement_id, timestamp, direction, docsis_version,
                    channel_id, frequency, modulation, power_level,
                    mer_mse_db, non_corr_errors, corr_errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                measurement_id,
                timestamp,
                ch.get('direction', ''),
                ch.get('docsis_version', ''),
                ch.get('channel_id', 0),
                ch.get('frequency', ''),
                ch.get('modulation', ''),
                ch.get('power_level', 0),
                ch.get('mer_mse_db', 0),
                ch.get('non_corr_errors', 0),
                ch.get('corr_errors', 0),
            ))
