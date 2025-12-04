# 🚀 Breitbandmessung - Einfach & Minimal# 🚀 Breitbandmessung - Einfach & Minimal# Breitbandmessung.de automated



Automatisierte Speedtests mit CSV-Export + FritzBox DSL-Diagnose - **schlank und simpel**.



## ✨ FeaturesAutomatisierte Speedtests mit CSV-Export - **schlank und simpel**.A script to enable customers of lazy ISPs to perform measurement campaigns of the connection speed as described [here](https://www.bundesnetzagentur.de/DE/Sachgebiete/Telekommunikation/Unternehmen_Institutionen/Breitband/Breitbandmessung/start.html) in an automated way.



- ✅ Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test)

- 📊 CSV-Export aller Messergebnisse

- 📡 **FritzBox DSL-Daten** (CRC-Fehler, SNR, Dämpfung, etc.) - **NEU!**## ✨ Features## Usage

- ⏰ Flexibler Zeitplan (Cron)

- 🐳 Docker & Docker Compose

- 💾 Nur 1 Config-Datei

- ✅ Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test)Create a configuration folder with the command `mkdir config` and inside the configuration folder a file `config.cfg`.

## 🚀 Schnellstart

- 📊 CSV-Export aller Messergebnisse

### 1. Repository klonen

- ⏰ Flexibler Zeitplan (Cron)Example config.cfg:

```bash

git clone https://github.com/Serph91P/breitbandmessung.git- 🐳 Docker & Docker Compose```

cd breitbandmessung

```- 💾 Nur 1 Config-Datei[Docker Config]



### 2. Konfiguration anpassentimezone=Europe/Berlin



Bearbeite `config.ini`:## 🚀 Schnellstartcrontab=* */2 * * *



```inirun_once=true

[Schedule]

cron_schedule = 0 */2 * * *    # Alle 2 Stunden### 1. Repository klonenrun_on_startup=true

timezone = Europe/Berlin

run_once = false                # Dauerhaft laufen

run_on_startup = true           # Sofort beim Start messen

```bash[Measurement]

[FritzBox]

enabled = true                  # FritzBox-Daten auslesengit clone https://github.com/Serph91P/breitbandmessung.gitmin-upload=600

host = 192.168.178.1           # FritzBox IP

```cd breitbandmessungmin-download=30



### 3. Pfad für CSV-Export setzen```



Erstelle `.env`:[Telegram]



```bash### 2. Konfiguration anpassen (optional)token=4927531485:lchtmxgr6sm7ia4g0fvbtoslruvgtway6uf

cp .env.example .env

nano .envID=42681397

```

Bearbeite `config.ini`:

```env

# Für Unraid z.B.:[MAIL]

EXPORT_PATH=/mnt/user/data/breitbandmessung

``````iniusername=firstname.lastname



### 4. Container starten[Schedule]password=supersecret



```bashcron_schedule = 0 */2 * * *    # Alle 2 Stundenmaildomain=gmail.com

docker-compose up -d

```timezone = Europe/Berlinmailto=mail.recipient@domain.com



### 5. Logs ansehenrun_once = false                # Dauerhaft laufen



```bashrun_on_startup = true           # Sofort beim Start messen[Twitter]

docker-compose logs -f

``````consumerkey=T1JJ3T3L2



## 📂 CSV-Dateienconsumersecret=A1BRTD4JD



Alle Messergebnisse werden als CSV im konfigurierten `EXPORT_PATH` gespeichert:### 3. Pfad für CSV-Export setzenaccesstoken=TIiajkdnlazkcOXrIdevi7F



```accesssecret=FDVJaj4jcl8chG3

messprotokolle/

├── breitbandmessung_04_12_2025_10_30_00.csvErstelle `.env`:

├── breitbandmessung_04_12_2025_12_30_00.csv

└── Breitbandmessung_04_12_2025_10_30_00.png[influxdb]

```

```bashhost=influxdb

## 📡 FritzBox Integration

cp .env.example .envport=8086

### Was wird ausgelesen?

nano .envdbname=breitbandmessung

Die FritzBox-Integration liest folgende DSL-Daten aus:

```

| Wert | Beschreibung |

|------|--------------|[influxdbv2]

| 📶 **Sync-Rate** | Tatsächliche DSL-Geschwindigkeit (Up/Down) in kbit/s |

| 📊 **SNR-Marge** | Signal-to-Noise Ratio in dB (je höher, desto besser) |```envhost=influxdb

| 📉 **Dämpfung** | Leitungsdämpfung in dB (je niedriger, desto besser) |

| 🔴 **CRC-Fehler** | **Nicht korrigierbare Fehler** (sollten bei 0 sein!) |# Für Unraid z.B.:port=8086

| 🟡 **FEC-Fehler** | Korrigierte Fehler |

| ✅ **Status** | DSL-Verbindungsstatus |EXPORT_PATH=/mnt/user/data/breitbandmessungdbname=breitbandmessung



### Konfiguration```orgname=MyOrganizationName



```initoken=SOYW1RRCbL6j0m5I6_UE6SMG3LHOirIhov2Y7NkPUcVHbaWIJZfdJT0h7geEaY5z42bz9SyuSjQ7GtTIsD43ev==

[FritzBox]

# Aktivieren### 4. Container starten

enabled = true

[prometheus]

# FritzBox IP (Standard: 192.168.178.1)

host = 192.168.178.1```bashgateway=http://prometheus-pushgateway:9091



# Login (nur wenn Benutzer-Auth aktiviert)docker-compose up -djob=breitbandmessung

username = 

password = ```instance=home

```



**Wichtig:** 

- Container muss im gleichen Netzwerk wie die FritzBox sein### 5. Logs ansehen```

- Keine Benutzer/Passwort nötig, wenn FritzBox-Login nicht aktiviert ist

- Bei Unraid: `network_mode: host` in docker-compose.yml nutzen



### CSV-Format mit FritzBox-Daten```bashCreate a folder for the measurement results with `mkdir messprotokolle`.



```csvdocker-compose logs -f

Datum;Zeit;Download (Mbit/s);Upload (Mbit/s);...;FB_CRC_Errors;FB_FEC_Errors;FB_Downstream_SNR;...

04.12.2025;10:30:00;1015.65;50.27;...;0;234;95;...```For the cronjob you can use [this website](https://crontab-generator.org/).

```

By default, the measurement is performed every 2nd full hour.

## ⚙️ Konfiguration

## 📂 CSV-Dateien

### Zeitplan

Timezone name from [this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List).

```ini

[Schedule]Alle Messergebnisse werden als CSV im konfigurierten `EXPORT_PATH` gespeichert:The default timezone is UTC.

# Cron-Format: Minute Stunde Tag Monat Wochentag

cron_schedule = 0 */2 * * *     # Alle 2 Stunden

```

```The broadband measurement can run once or automated via cron.

**Beispiele:**

- `0 * * * *` = Jede Stundemessprotokolle/For a one-time measurement set the value in the config to true.

- `0 8,20 * * *` = Um 8 und 20 Uhr

- `*/30 * * * *` = Alle 30 Minuten├── breitbandmessung_04_12_2025_10_30_00.csv

- `0 0 * * *` = Täglich um Mitternacht

├── breitbandmessung_04_12_2025_12_30_00.csv

### Einmalige Messung

└── Breitbandmessung_04_12_2025_10_30_00.png

Für einen einzelnen Test:

```Just run:

```ini

run_once = true

run_on_startup = true

```## ⚙️ Konfiguration```



Container stoppt nach der Messung automatisch.git clone https://github.com/shneezin/breitbandmessung.git && cd breitbandmessung



### ScreenshotsAlles wird in `config.ini` eingestellt:sudo ./create.sh



```ini```

[Settings]

save_screenshots = true### Zeitplan

```

or 

## 🛠️ Befehle

```ini

```bash

# Start[Schedule]```

docker-compose up -d

# Cron-Format: Minute Stunde Tag Monat Wochentagdocker run -d -v $PWD/config/:/usr/src/app/config:rw -v $PWD/messprotokolle:/export/ --name "breitbandmessung" shneezin/breitbandmessung

# Stop

docker-compose downcron_schedule = 0 */2 * * *     # Alle 2 Stunden```



# Logs ansehen```

docker-compose logs -f

To merge the csv files into one, run merge.sh or:

# Neustart

docker-compose restart**Beispiele:**```



# Status- `0 * * * *` = Jede Stundewget -O - https://raw.githubusercontent.com/shneezin/breitbandmessung/master/merge.sh | bash

docker-compose ps

- `0 8,20 * * *` = Um 8 und 20 Uhr```

# Manuelle Messung

docker-compose exec breitbandmessung /usr/src/app/speedtest.py- `*/30 * * * *` = Alle 30 Minuten



# Rebuild- `0 0 * * *` = Täglich um Mitternacht## New Features

docker-compose up -d --build

```



## 📋 Für Unraid### Einmalige Messung### Prometheus Support



### Docker Compose PluginThe script now supports pushing metrics to Prometheus via a Pushgateway. Configure the `[prometheus]` section in your config.cfg:



1. Installiere **Docker Compose Manager** aus Community AppsFür einen einzelnen Test:- `gateway`: URL of your Prometheus Pushgateway

2. Erstelle Stack mit `docker-compose.yml`

3. Setze `EXPORT_PATH=/mnt/user/data/breitbandmessung`- `job`: Job name for the metrics (default: breitbandmessung)

4. Für FritzBox: Füge `network_mode: host` hinzu

5. Start!```ini- `instance`: Instance identifier (default: default)



### docker-compose.yml für Unraidrun_once = true



```yamlrun_on_startup = true### Automatic Firefox Profile Cleanup

version: '3.8'

```The script now automatically cleans up Firefox profiles in `/tmp` after each run to prevent disk space issues that could accumulate over time.

services:

  breitbandmessung:

    build: .

    container_name: breitbandmessungContainer stoppt nach der Messung automatisch.### Export Directory Creation

    restart: unless-stopped

    network_mode: host  # Wichtig für FritzBox-Zugriff!The script automatically creates the `/export` directory if it doesn't exist, ensuring measurement results are properly saved.

    

    volumes:### Screenshots

      - /mnt/user/data/breitbandmessung:/export

      - ./config.ini:/usr/src/app/config/config.ini:ro### Fixed Cron Scheduling

```

```iniFixed issues with cron scheduling where escaped asterisks in the cron expression caused measurements to run every minute instead of the configured schedule.

### Oder manuell via Terminal

[Settings]

```bash

cd /mnt/user/appdata/save_screenshots = true## Configuration Examples

git clone https://github.com/Serph91P/breitbandmessung.git

cd breitbandmessung```



# Aktiviere FritzBox in config.ini### Cron Schedule Examples

nano config.ini

## 🛠️ Befehle- `0 */2 * * *` - Every 2 hours at minute 0

# Setze Export-Pfad

echo "EXPORT_PATH=/mnt/user/data/breitbandmessung" > .env- `47 3 * * *` - Every day at 3:47 AM



docker-compose up -d```bash- `0 9,17 * * 1-5` - At 9:00 AM and 5:00 PM on weekdays

```

# Start

## 🐛 Troubleshooting

docker-compose up -d**Note**: Do not escape asterisks with backslashes in the cron configuration.

### Container startet nicht



```bash

docker-compose logs# StopThanks to shiaky for the idea on this project. 

```

docker-compose downYou can find his repo [here](https://github.com/shiaky/breitbandmessung)

### Keine CSV-Dateien



Prüfe Volume-Mount:

# Logs ansehen## License

```bash

docker-compose exec breitbandmessung ls -la /exportdocker-compose logs -f

```

Feel free to use and improve the script as you like. I take no responsibility for the script.

### FritzBox nicht erreichbar

# Neustart

```bashdocker-compose restart

# Teste FritzBox-Erreichbarkeit

docker-compose exec breitbandmessung ping -c 3 192.168.178.1# Status

docker-compose ps

# Prüfe Netzwerk-Modus

docker inspect breitbandmessung | grep NetworkMode# Manuelle Messung

```docker-compose exec breitbandmessung /usr/src/app/speedtest.py



Für FritzBox-Zugriff muss der Container im gleichen Netzwerk sein:# Rebuild

- Entweder `network_mode: host`docker-compose up -d --build

- Oder FritzBox über Bridge-Netzwerk erreichbar```



### Test manuell ausführen## 📋 Für Unraid



```bash### Docker Compose Plugin

docker-compose exec breitbandmessung /usr/src/app/speedtest.py

```1. Installiere **Docker Compose Manager** aus Community Apps

2. Erstelle Stack mit `docker-compose.yml`

## 📝 Was ist neu?3. Setze `EXPORT_PATH=/mnt/user/data/breitbandmessung`

4. Start!

### Version 3.0 - FritzBox Edition

### Oder manuell via Terminal

- ✅ **FritzBox DSL-Diagnose** via TR-064 API

- ✅ **CRC-Fehler** werden jetzt mitgeloggt```bash

- ✅ **SNR & Dämpfung** in CSV exportiertcd /mnt/user/appdata/

- ✅ Automatische CSV-Erweiterung mit DSL-Datengit clone https://github.com/Serph91P/breitbandmessung.git

cd breitbandmessung

### Ultra-minimalistisch:

# Setze Export-Pfad

- ❌ Keine Benachrichtigungen (Telegram, E-Mail, Twitter)echo "EXPORT_PATH=/mnt/user/data/breitbandmessung" > .env

- ❌ Kein Monitoring (InfluxDB, Prometheus)

- ❌ Keine komplexen Dependencies (Rust, Cryptography)docker-compose up -d

- ✅ Nur: **Selenium + Firefox + CSV + FritzBox API**```



## 📊 Beispiel-Output## 🐛 Troubleshooting



```### Container startet nicht

==================================================

📊 MESSERGEBNISSE:```bash

==================================================docker-compose logs

  📥 Download: 1015.65 Mbit/s```

  📤 Upload:   50.27 Mbit/s

  ⚡ Ping:     14 ms### Keine CSV-Dateien



📡 FritzBox DSL-Info:Prüfe Volume-Mount:

  📶 Sync: 1200.0 / 51.8 Mbit/s

  📊 SNR: 9.5 / 9.2 dB```bash

  📉 Dämpfung: 15.3 / 10.8 dBdocker-compose exec breitbandmessung ls -la /export

  🔴 CRC Fehler: 0```

  🟡 FEC Fehler: 234

==================================================### Test manuell ausführen



💾 CSV gespeichert: Breitbandmessung_04_12_2025_10_30_00.csv```bash

```docker-compose exec breitbandmessung /usr/src/app/speedtest.py

```

## 🎯 Warum FritzBox-Daten?

## 📝 Was wurde entfernt?

**CRC-Fehler** sind nicht korrigierbare Übertragungsfehler auf der DSL-Leitung. Wenn diese Zahl hoch ist:

- 🔴 Schlechte LeitungsqualitätDiese Version ist **ultra-minimalistisch**:

- 🔴 Möglicherweise defekte Hardware

- 🔴 Störungen auf der Leitung- ❌ Keine Benachrichtigungen (Telegram, E-Mail, Twitter)

- 📧 **Wichtig für Provider-Meldung!**- ❌ Kein Monitoring (InfluxDB, Prometheus)

- ❌ Keine komplexen Dependencies (Rust, Cryptography)

Mit diesen Daten kannst du gegenüber deinem Provider **technisch beweisen**, dass Probleme auf der Leitung existieren!- ✅ Nur das Nötigste: **Selenium + Firefox + CSV**



## 📄 Lizenz## 📊 CSV-Format



MIT```csv

Datum;Zeit;Download (Mbit/s);Upload (Mbit/s);Laufzeit (ms);...

---04.12.2025;10:30:00;52,5;12,3;15;...

```

**Minimalistisch. Funktional. Mit FritzBox-Power.** 🎯📡

## 📄 Lizenz

MIT

---

**Minimalistisch. Funktional. Fertig.** 🎯
