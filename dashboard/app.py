#!/usr/bin/env python3
"""
Breitbandmessung Dashboard - Streamlit Web-Interface
Zeigt Speedtest-Ergebnisse und FritzBox-Analysen interaktiv an.
Liest Daten aus SQLite-Datenbank (mit CSV-Fallback).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import glob

# Seiten-Konfiguration
st.set_page_config(
    page_title="Breitbandmessung Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Pfade
MESSPROTOKOLLE_DIR = Path("/data")
DB_PATH = MESSPROTOKOLLE_DIR / "measurements.db"


def get_db_connection():
    """Erstellt eine SQLite-Verbindung"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def clean_numeric(series):
    """Konvertiert String mit deutschem Dezimalformat zu Float"""
    if hasattr(series, 'str'):
        return pd.to_numeric(
            series.str.replace('"', '').str.replace(',', '.'), 
            errors='coerce'
        )
    return pd.to_numeric(series, errors='coerce')


@st.cache_data(ttl=60)
def load_measurements():
    """Lädt alle Messdaten aus SQLite (mit CSV-Fallback)"""
    
    # Primär: aus SQLite lesen
    if DB_PATH.exists():
        try:
            conn = get_db_connection()
            df = pd.read_sql_query("""
                SELECT 
                    test_id AS "Test-ID",
                    date AS "Messzeitpunkt",
                    time AS "Uhrzeit",
                    download_mbps AS "Download (Mbit/s)",
                    upload_mbps AS "Upload (Mbit/s)",
                    ping_ms AS "Laufzeit (ms)",
                    version AS "Version",
                    os AS "Betriebssystem",
                    browser AS "Internet-Browser",
                    datetime,
                    fb_non_corr_errors AS "FB_Non_Corr_Errors",
                    fb_corr_errors AS "FB_Corr_Errors",
                    fb_docsis31_ds AS "FB_DOCSIS31_DS",
                    fb_docsis30_ds AS "FB_DOCSIS30_DS",
                    fb_docsis31_us AS "FB_DOCSIS31_US",
                    fb_docsis30_us AS "FB_DOCSIS30_US",
                    fb_avg_ds_power AS "FB_Avg_DS_Power_dBmV",
                    fb_min_ds_power AS "FB_Min_DS_Power_dBmV",
                    fb_max_ds_power AS "FB_Max_DS_Power_dBmV",
                    fb_avg_us_power AS "FB_Avg_US_Power_dBmV",
                    fb_sync_ds_kbps AS "FB_Sync_DS_Kbps",
                    fb_sync_us_kbps AS "FB_Sync_US_Kbps",
                    fb_connection_time AS "FB_Connection_Time"
                FROM measurements 
                ORDER BY datetime ASC
            """, conn)
            conn.close()
            
            if not df.empty:
                df['Datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
                df = df.drop(columns=['datetime'])
                df['Stunde'] = df['Datetime'].dt.hour
                df['Wochentag'] = df['Datetime'].dt.day_name()
                df['Datum'] = df['Datetime'].dt.date
                return df
        except Exception as e:
            st.toast(f"⚠️ DB-Lesefehler: {e}", icon="⚠️")
    
    # Fallback: CSV-Dateien laden
    return _load_measurements_csv()


def _load_measurements_csv():
    """Fallback: Lädt Messdaten aus CSV-Dateien"""
    messergebnisse_file = MESSPROTOKOLLE_DIR / "messergebnisse.csv"
    
    if messergebnisse_file.exists():
        df = pd.read_csv(messergebnisse_file, sep=';', encoding='utf-8')
    else:
        alle_dateien = sorted(MESSPROTOKOLLE_DIR.glob("Breitbandmessung_*.csv"))
        alle_dateien = [f for f in alle_dateien if not f.name.endswith('_docsis.csv')]
        
        if not alle_dateien:
            return pd.DataFrame()
        
        dataframes = []
        for datei in alle_dateien:
            try:
                result = pd.read_csv(datei, sep=';', encoding='utf-8')
                if not result.empty:
                    dataframes.append(result)
            except Exception:
                pass
        
        if not dataframes:
            return pd.DataFrame()
        
        df = pd.concat(dataframes, ignore_index=True)
        df = df.drop_duplicates(subset=['Test-ID'], keep='first')
    
    if df.empty:
        return df
    
    # Daten bereinigen
    df['Download (Mbit/s)'] = clean_numeric(df['Download (Mbit/s)'])
    df['Upload (Mbit/s)'] = clean_numeric(df['Upload (Mbit/s)'])
    df['Laufzeit (ms)'] = clean_numeric(df['Laufzeit (ms)'])
    
    # Datetime erstellen
    df['Datetime'] = pd.to_datetime(
        df['Messzeitpunkt'].str.replace('"', '') + ' ' + df['Uhrzeit'].str.replace('"', ''), 
        format='%d.%m.%Y %H:%M:%S',
        errors='coerce'
    )
    df['Stunde'] = df['Datetime'].dt.hour
    df['Wochentag'] = df['Datetime'].dt.day_name()
    df['Datum'] = df['Datetime'].dt.date
    
    for col in df.columns:
        if col.startswith('FB_') and col not in ['FB_Connection_Time']:
            df[col] = clean_numeric(df[col])
    
    return df.sort_values('Datetime')


@st.cache_data(ttl=60)
def load_docsis_history():
    """Lädt DOCSIS-Kanal-Historie aus SQLite (mit CSV-Fallback)"""
    
    # Primär: aus SQLite
    if DB_PATH.exists():
        try:
            conn = get_db_connection()
            df = pd.read_sql_query("""
                SELECT 
                    dc.timestamp,
                    dc.direction,
                    dc.docsis_version,
                    dc.channel_id,
                    dc.frequency,
                    dc.modulation,
                    dc.power_level,
                    dc.mer_mse_db,
                    dc.non_corr_errors,
                    dc.corr_errors
                FROM docsis_channels dc
                ORDER BY dc.timestamp ASC, dc.channel_id ASC
            """, conn)
            conn.close()
            if not df.empty:
                return df
        except Exception:
            pass
    
    # Fallback: CSV-Dateien
    docsis_file = MESSPROTOKOLLE_DIR / "docsis_historie.csv"
    if docsis_file.exists():
        return pd.read_csv(docsis_file, sep=';', encoding='utf-8')
    
    # Alternativ: Sammle alle _docsis.csv Dateien
    docsis_files = sorted(MESSPROTOKOLLE_DIR.glob("*_docsis.csv"))
    if docsis_files:
        dfs = []
        for f in docsis_files:
            try:
                dfs.append(pd.read_csv(f, sep=';', encoding='utf-8'))
            except Exception:
                pass
        if dfs:
            return pd.concat(dfs, ignore_index=True)
    
    return pd.DataFrame()


def render_sidebar(df):
    """Sidebar mit Filtern"""
    st.sidebar.header("🔧 Filter")
    
    if df.empty:
        return df
    
    # Zeitraum-Filter
    min_date = df['Datetime'].min().date()
    max_date = df['Datetime'].max().date()
    
    st.sidebar.subheader("📅 Zeitraum")
    date_range = st.sidebar.date_input(
        "Datum",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        df = df[(df['Datum'] >= start_date) & (df['Datum'] <= end_date)]
    
    # Tageszeit-Filter
    st.sidebar.subheader("🕐 Tageszeit")
    hours = st.sidebar.slider("Stunden", 0, 23, (0, 23))
    df = df[(df['Stunde'] >= hours[0]) & (df['Stunde'] <= hours[1])]
    
    # Info
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 {len(df)} Messungen im Filter")
    
    return df


def render_overview(df):
    """Übersichts-KPIs"""
    st.header("📊 Übersicht")
    
    if df.empty:
        st.warning("Keine Daten vorhanden")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_download = df['Download (Mbit/s)'].mean()
        st.metric(
            "⬇️ Ø Download",
            f"{avg_download:.1f} Mbit/s",
            delta=f"{avg_download - 1000:.0f}" if avg_download < 1000 else None,
            delta_color="normal"
        )
    
    with col2:
        avg_upload = df['Upload (Mbit/s)'].mean()
        st.metric(
            "⬆️ Ø Upload",
            f"{avg_upload:.1f} Mbit/s"
        )
    
    with col3:
        avg_ping = df['Laufzeit (ms)'].mean()
        st.metric(
            "📶 Ø Latenz",
            f"{avg_ping:.1f} ms"
        )
    
    with col4:
        problem_count = len(df[df['Download (Mbit/s)'] < 800])
        st.metric(
            "⚠️ Probleme",
            f"{problem_count} / {len(df)}",
            delta=f"{problem_count/len(df)*100:.0f}%" if len(df) > 0 else "0%",
            delta_color="inverse"
        )
    
    # Statistik-Tabelle
    with st.expander("📈 Detaillierte Statistik"):
        stats_data = {
            "Metrik": ["Download (Mbit/s)", "Upload (Mbit/s)", "Latenz (ms)"],
            "Durchschnitt": [
                f"{df['Download (Mbit/s)'].mean():.1f}",
                f"{df['Upload (Mbit/s)'].mean():.1f}",
                f"{df['Laufzeit (ms)'].mean():.1f}"
            ],
            "Minimum": [
                f"{df['Download (Mbit/s)'].min():.1f}",
                f"{df['Upload (Mbit/s)'].min():.1f}",
                f"{df['Laufzeit (ms)'].min():.1f}"
            ],
            "Maximum": [
                f"{df['Download (Mbit/s)'].max():.1f}",
                f"{df['Upload (Mbit/s)'].max():.1f}",
                f"{df['Laufzeit (ms)'].max():.1f}"
            ],
            "Std.Abw.": [
                f"{df['Download (Mbit/s)'].std():.1f}",
                f"{df['Upload (Mbit/s)'].std():.1f}",
                f"{df['Laufzeit (ms)'].std():.1f}"
            ]
        }
        st.table(pd.DataFrame(stats_data))


def render_speedtest_chart(df):
    """Speedtest Zeitverlauf"""
    st.header("📈 Speedtest Zeitverlauf")
    
    if df.empty:
        st.warning("Keine Daten vorhanden")
        return
    
    tab1, tab2 = st.tabs(["📥 Download", "📤 Upload"])
    
    with tab1:
        fig = go.Figure()
        
        # Download-Linie
        fig.add_trace(go.Scatter(
            x=df['Datetime'],
            y=df['Download (Mbit/s)'],
            mode='lines+markers',
            name='Download',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=4)
        ))
        
        # Grenzlinien
        fig.add_hline(y=1000, line_dash="dash", line_color="green", 
                      annotation_text="Vertraglich (1000 Mbit/s)")
        fig.add_hline(y=800, line_dash="dash", line_color="orange", 
                      annotation_text="80% Schwelle")
        fig.add_hline(y=500, line_dash="dash", line_color="red", 
                      annotation_text="Kritisch")
        
        fig.update_layout(
            title="Download-Geschwindigkeit über Zeit",
            xaxis_title="Datum/Zeit",
            yaxis_title="Download (Mbit/s)",
            yaxis=dict(range=[0, 1200]),
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with tab2:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['Datetime'],
            y=df['Upload (Mbit/s)'],
            mode='lines+markers',
            name='Upload',
            line=dict(color='#2ca02c', width=2),
            marker=dict(size=4)
        ))
        
        fig.add_hline(y=50, line_dash="dash", line_color="green", 
                      annotation_text="Vertraglich (~50 Mbit/s)")
        fig.add_hline(y=40, line_dash="dash", line_color="orange", 
                      annotation_text="80% Schwelle")
        
        fig.update_layout(
            title="Upload-Geschwindigkeit über Zeit",
            xaxis_title="Datum/Zeit",
            yaxis_title="Upload (Mbit/s)",
            yaxis=dict(range=[0, 60]),
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig, width="stretch")


def render_hourly_analysis(df):
    """Analyse nach Tageszeit"""
    st.header("🕐 Analyse nach Tageszeit")
    
    if df.empty:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        hourly = df.groupby('Stunde').agg({
            'Download (Mbit/s)': ['mean', 'min', 'max', 'count']
        }).reset_index()
        hourly.columns = ['Stunde', 'Durchschnitt', 'Minimum', 'Maximum', 'Anzahl']
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=hourly['Stunde'],
            y=hourly['Durchschnitt'],
            name='Durchschnitt',
            marker_color='#1f77b4',
            opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=hourly['Stunde'],
            y=hourly['Minimum'],
            mode='markers',
            name='Minimum',
            marker=dict(color='red', size=10)
        ))
        
        fig.add_hline(y=1000, line_dash="dash", line_color="green")
        fig.add_hline(y=800, line_dash="dash", line_color="orange")
        
        fig.update_layout(
            title="Download nach Tageszeit",
            xaxis_title="Stunde",
            yaxis_title="Download (Mbit/s)",
            xaxis=dict(tickmode='linear', dtick=2),
            height=400
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        hourly_up = df.groupby('Stunde').agg({
            'Upload (Mbit/s)': ['mean', 'min', 'max']
        }).reset_index()
        hourly_up.columns = ['Stunde', 'Durchschnitt', 'Minimum', 'Maximum']
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=hourly_up['Stunde'],
            y=hourly_up['Durchschnitt'],
            name='Durchschnitt',
            marker_color='#2ca02c',
            opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=hourly_up['Stunde'],
            y=hourly_up['Minimum'],
            mode='markers',
            name='Minimum',
            marker=dict(color='red', size=10)
        ))
        
        fig.add_hline(y=50, line_dash="dash", line_color="green")
        fig.add_hline(y=40, line_dash="dash", line_color="orange")
        
        fig.update_layout(
            title="Upload nach Tageszeit",
            xaxis_title="Stunde",
            yaxis_title="Upload (Mbit/s)",
            xaxis=dict(tickmode='linear', dtick=2),
            height=400
        )
        st.plotly_chart(fig, width="stretch")


def render_fritzbox_analysis(df):
    """FritzBox/DOCSIS Fehleranalyse"""
    st.header("🚨 DOCSIS Fehleranalyse")
    
    if 'FB_Non_Corr_Errors' not in df.columns:
        st.info("ℹ️ Keine FritzBox-Daten in den Messungen vorhanden. Aktiviere FritzBox in der config.ini")
        return
    
    df_fb = df[df['FB_Non_Corr_Errors'].notna()].copy()
    
    if df_fb.empty:
        st.warning("Keine FritzBox-Daten in den gefilterten Messungen")
        return
    
    # Aktuelle Fehlerwerte
    aktuell = df_fb.iloc[-1]
    erster = df_fb.iloc[0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🔴 Nicht korrigierbare Fehler",
            f"{aktuell['FB_Non_Corr_Errors']:,.0f}"
        )
    
    with col2:
        if 'FB_Corr_Errors' in df_fb.columns:
            st.metric(
                "🟡 Korrigierbare Fehler",
                f"{aktuell['FB_Corr_Errors']:,.0f}"
            )
    
    with col3:
        if len(df_fb) > 1:
            fehler_start = erster['FB_Non_Corr_Errors']
            fehler_ende = aktuell['FB_Non_Corr_Errors']
            fehler_zuwachs = fehler_ende - fehler_start
            
            zeit_start = df_fb['Datetime'].iloc[0]
            zeit_ende = df_fb['Datetime'].iloc[-1]
            stunden = (zeit_ende - zeit_start).total_seconds() / 3600
            
            if stunden > 0:
                fehler_pro_stunde = fehler_zuwachs / stunden
                st.metric(
                    "⏱️ Fehler pro Stunde",
                    f"{fehler_pro_stunde:,.0f}"
                )
    
    # Fehler-Zeitverlauf
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=('Kumulative Fehler', 'Fehlerzuwachs pro Messung'),
                        vertical_spacing=0.15)
    
    # Plot 1: Kumulative Fehler
    fig.add_trace(
        go.Scatter(x=df_fb['Datetime'], y=df_fb['FB_Non_Corr_Errors'],
                   mode='lines+markers', name='Nicht korrigierbar',
                   line=dict(color='red')),
        row=1, col=1
    )
    
    if 'FB_Corr_Errors' in df_fb.columns:
        fig.add_trace(
            go.Scatter(x=df_fb['Datetime'], y=df_fb['FB_Corr_Errors'],
                       mode='lines+markers', name='Korrigierbar',
                       line=dict(color='orange'), opacity=0.7),
            row=1, col=1
        )
    
    # Plot 2: Fehlerdifferenz
    fehler_diff = df_fb['FB_Non_Corr_Errors'].diff().fillna(0)
    colors = ['red' if x > 0 else 'green' for x in fehler_diff]
    
    fig.add_trace(
        go.Bar(x=df_fb['Datetime'], y=fehler_diff, name='Zuwachs',
               marker_color=colors),
        row=2, col=1
    )
    
    fig.update_layout(height=600, showlegend=True,
                      title_text="DOCSIS-Fehler über Zeit")
    fig.update_yaxes(title_text="Fehleranzahl", row=1, col=1)
    fig.update_yaxes(title_text="Neue Fehler", row=2, col=1)
    
    st.plotly_chart(fig, width="stretch")
    
    # Signalpegel falls vorhanden
    if 'FB_Avg_DS_Power_dBmV' in df_fb.columns:
        st.subheader("📶 Signalpegel")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure()
            
            if 'FB_Min_DS_Power_dBmV' in df_fb.columns and 'FB_Max_DS_Power_dBmV' in df_fb.columns:
                fig.add_trace(go.Scatter(
                    x=df_fb['Datetime'],
                    y=df_fb['FB_Max_DS_Power_dBmV'],
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False
                ))
                fig.add_trace(go.Scatter(
                    x=df_fb['Datetime'],
                    y=df_fb['FB_Min_DS_Power_dBmV'],
                    mode='lines',
                    fill='tonexty',
                    fillcolor='rgba(31, 119, 180, 0.3)',
                    line=dict(width=0),
                    name='Min-Max Bereich'
                ))
            
            fig.add_trace(go.Scatter(
                x=df_fb['Datetime'],
                y=df_fb['FB_Avg_DS_Power_dBmV'],
                mode='lines',
                name='Durchschnitt',
                line=dict(color='#1f77b4', width=2)
            ))
            
            fig.add_hline(y=10, line_dash="dash", line_color="orange", 
                          annotation_text="Oberer Grenzwert")
            fig.add_hline(y=-7, line_dash="dash", line_color="orange", 
                          annotation_text="Unterer Grenzwert")
            
            fig.update_layout(
                title="Downstream Signalpegel",
                xaxis_title="Datum",
                yaxis_title="Power Level (dBmV)",
                height=350
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            if 'FB_Avg_US_Power_dBmV' in df_fb.columns:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_fb['Datetime'],
                    y=df_fb['FB_Avg_US_Power_dBmV'],
                    mode='lines+markers',
                    name='Upstream Power',
                    line=dict(color='#2ca02c', width=2),
                    marker=dict(size=4)
                ))
                
                fig.add_hline(y=45, line_dash="dash", line_color="red", 
                              annotation_text="Max (45 dBmV)")
                fig.add_hline(y=35, line_dash="dash", line_color="orange")
                fig.add_hline(y=42, line_dash="dash", line_color="orange")
                
                fig.update_layout(
                    title="Upstream Signalpegel",
                    xaxis_title="Datum",
                    yaxis_title="Power Level (dBmV)",
                    height=350
                )
                st.plotly_chart(fig, width="stretch")


def render_correlation_analysis(df):
    """Korrelationsanalyse"""
    st.header("🔗 Korrelationsanalyse")
    
    if 'FB_Non_Corr_Errors' not in df.columns:
        st.info("ℹ️ Keine FritzBox-Daten für Korrelationsanalyse verfügbar")
        return
    
    df_fb = df[df['FB_Non_Corr_Errors'].notna()].copy()
    
    if len(df_fb) < 2:
        st.warning("Zu wenige Datenpunkte für Korrelationsanalyse")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.scatter(
            df_fb,
            x='FB_Non_Corr_Errors',
            y='Download (Mbit/s)',
            color='Stunde',
            color_continuous_scale='Viridis',
            title="Download vs. DOCSIS-Fehler",
            labels={'FB_Non_Corr_Errors': 'Kumulative Fehler'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch")
        
        corr_down = df_fb['FB_Non_Corr_Errors'].corr(df_fb['Download (Mbit/s)'])
        st.info(f"📊 Korrelation: {corr_down:.3f}")
    
    with col2:
        fig = px.scatter(
            df_fb,
            x='FB_Non_Corr_Errors',
            y='Upload (Mbit/s)',
            color='Stunde',
            color_continuous_scale='Viridis',
            title="Upload vs. DOCSIS-Fehler",
            labels={'FB_Non_Corr_Errors': 'Kumulative Fehler'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch")
        
        corr_up = df_fb['FB_Non_Corr_Errors'].corr(df_fb['Upload (Mbit/s)'])
        st.info(f"📊 Korrelation: {corr_up:.3f}")


def render_worst_measurements(df):
    """Zeigt die schlechtesten Messungen"""
    st.header("🔴 Problematische Messungen")
    
    if df.empty:
        return
    
    tab1, tab2 = st.tabs(["Schlechteste Downloads", "Schlechteste Uploads"])
    
    cols = ['Datetime', 'Download (Mbit/s)', 'Upload (Mbit/s)', 'Laufzeit (ms)']
    if 'FB_Non_Corr_Errors' in df.columns:
        cols.append('FB_Non_Corr_Errors')
    
    with tab1:
        worst_download = df.nsmallest(10, 'Download (Mbit/s)')[cols].copy()
        worst_download['Datetime'] = worst_download['Datetime'].dt.strftime('%d.%m.%Y %H:%M')
        st.dataframe(worst_download, width="stretch", hide_index=True)
    
    with tab2:
        worst_upload = df.nsmallest(10, 'Upload (Mbit/s)')[cols].copy()
        worst_upload['Datetime'] = worst_upload['Datetime'].dt.strftime('%d.%m.%Y %H:%M')
        st.dataframe(worst_upload, width="stretch", hide_index=True)


def render_raw_data(df):
    """Rohdaten-Ansicht"""
    st.header("📋 Rohdaten")
    
    if df.empty:
        return
    
    # Spaltenauswahl
    all_cols = list(df.columns)
    default_cols = ['Datetime', 'Download (Mbit/s)', 'Upload (Mbit/s)', 'Laufzeit (ms)']
    default_cols = [c for c in default_cols if c in all_cols]
    
    selected_cols = st.multiselect(
        "Spalten auswählen",
        all_cols,
        default=default_cols
    )
    
    if selected_cols:
        display_df = df[selected_cols].copy()
        if 'Datetime' in selected_cols:
            display_df['Datetime'] = display_df['Datetime'].dt.strftime('%d.%m.%Y %H:%M')
        st.dataframe(display_df, width="stretch", hide_index=True)
        
        # Download-Button
        csv = df[selected_cols].to_csv(index=False, sep=';')
        st.download_button(
            label="📥 Als CSV herunterladen",
            data=csv,
            file_name=f"breitbandmessung_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def main():
    """Hauptfunktion"""
    st.title("📡 Breitbandmessung Dashboard")
    st.markdown("Übersicht aller Speedtest-Ergebnisse und FritzBox-Analysen")
    
    # Daten laden
    with st.spinner("Lade Daten..."):
        df = load_measurements()
    
    if df.empty:
        st.error("❌ Keine Messdaten gefunden!")
        st.markdown("""
        ### Mögliche Ursachen:
        1. Kein Datenverzeichnis gemountet
        2. Noch keine Messungen durchgeführt
        3. Datenbank noch nicht erstellt (CSV-Import noch nicht gelaufen)
        
        Stelle sicher, dass das `/data` Verzeichnis die Datenbank oder CSV-Dateien enthält.
        """)
        return
    
    # Datenquelle anzeigen
    data_source = "SQLite" if DB_PATH.exists() else "CSV-Dateien"
    st.sidebar.caption(f"📦 Datenquelle: {data_source}")
    
    # Sidebar Filter
    df_filtered = render_sidebar(df)
    
    # Navigation
    page = st.sidebar.radio(
        "📍 Navigation",
        ["Übersicht", "Zeitverlauf", "Tageszeit-Analyse", "DOCSIS-Analyse", 
         "Korrelation", "Probleme", "Rohdaten"]
    )
    
    # Seiten rendern
    if page == "Übersicht":
        render_overview(df_filtered)
        st.markdown("---")
        render_speedtest_chart(df_filtered)
    elif page == "Zeitverlauf":
        render_speedtest_chart(df_filtered)
    elif page == "Tageszeit-Analyse":
        render_hourly_analysis(df_filtered)
    elif page == "DOCSIS-Analyse":
        render_fritzbox_analysis(df_filtered)
    elif page == "Korrelation":
        render_correlation_analysis(df_filtered)
    elif page == "Probleme":
        render_worst_measurements(df_filtered)
    elif page == "Rohdaten":
        render_raw_data(df_filtered)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"🕐 Letzte Messung: **{df['Datetime'].max().strftime('%d.%m.%Y %H:%M')}**")
    st.sidebar.markdown(f"📊 Gesamt: **{len(df)}** Messungen")


if __name__ == "__main__":
    main()
