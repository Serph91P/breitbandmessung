# 🚀 Breitbandmessung - Einfach & Minimal# Breitbandmessung.de automated



Automatisierte Speedtests mit CSV-Export - **schlank und simpel**.A script to enable customers of lazy ISPs to perform measurement campaigns of the connection speed as described [here](https://www.bundesnetzagentur.de/DE/Sachgebiete/Telekommunikation/Unternehmen_Institutionen/Breitband/Breitbandmessung/start.html) in an automated way.



## ✨ Features## Usage



- ✅ Automatische Speedtests via [breitbandmessung.de](https://breitbandmessung.de/test)Create a configuration folder with the command `mkdir config` and inside the configuration folder a file `config.cfg`.

- 📊 CSV-Export aller Messergebnisse

- ⏰ Flexibler Zeitplan (Cron)Example config.cfg:

- 🐳 Docker & Docker Compose```

- 💾 Nur 1 Config-Datei[Docker Config]

timezone=Europe/Berlin

## 🚀 Schnellstartcrontab=* */2 * * *

run_once=true

### 1. Repository klonenrun_on_startup=true



```bash[Measurement]

git clone https://github.com/Serph91P/breitbandmessung.gitmin-upload=600

cd breitbandmessungmin-download=30

```

[Telegram]

### 2. Konfiguration anpassen (optional)token=4927531485:lchtmxgr6sm7ia4g0fvbtoslruvgtway6uf

ID=42681397

Bearbeite `config.ini`:

[MAIL]

```iniusername=firstname.lastname

[Schedule]password=supersecret

cron_schedule = 0 */2 * * *    # Alle 2 Stundenmaildomain=gmail.com

timezone = Europe/Berlinmailto=mail.recipient@domain.com

run_once = false                # Dauerhaft laufen

run_on_startup = true           # Sofort beim Start messen[Twitter]

```consumerkey=T1JJ3T3L2

consumersecret=A1BRTD4JD

### 3. Pfad für CSV-Export setzenaccesstoken=TIiajkdnlazkcOXrIdevi7F

accesssecret=FDVJaj4jcl8chG3

Erstelle `.env`:

[influxdb]

```bashhost=influxdb

cp .env.example .envport=8086

nano .envdbname=breitbandmessung

```

[influxdbv2]

```envhost=influxdb

# Für Unraid z.B.:port=8086

EXPORT_PATH=/mnt/user/data/breitbandmessungdbname=breitbandmessung

```orgname=MyOrganizationName

token=SOYW1RRCbL6j0m5I6_UE6SMG3LHOirIhov2Y7NkPUcVHbaWIJZfdJT0h7geEaY5z42bz9SyuSjQ7GtTIsD43ev==

### 4. Container starten

[prometheus]

```bashgateway=http://prometheus-pushgateway:9091

docker-compose up -djob=breitbandmessung

```instance=home



### 5. Logs ansehen```



```bashCreate a folder for the measurement results with `mkdir messprotokolle`.

docker-compose logs -f

```For the cronjob you can use [this website](https://crontab-generator.org/).

By default, the measurement is performed every 2nd full hour.

## 📂 CSV-Dateien

Timezone name from [this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List).

Alle Messergebnisse werden als CSV im konfigurierten `EXPORT_PATH` gespeichert:The default timezone is UTC.



```The broadband measurement can run once or automated via cron.

messprotokolle/For a one-time measurement set the value in the config to true.

├── breitbandmessung_04_12_2025_10_30_00.csv

├── breitbandmessung_04_12_2025_12_30_00.csv

└── Breitbandmessung_04_12_2025_10_30_00.png

```Just run:



## ⚙️ Konfiguration```

git clone https://github.com/shneezin/breitbandmessung.git && cd breitbandmessung

Alles wird in `config.ini` eingestellt:sudo ./create.sh

```

### Zeitplan

or 

```ini

[Schedule]```

# Cron-Format: Minute Stunde Tag Monat Wochentagdocker run -d -v $PWD/config/:/usr/src/app/config:rw -v $PWD/messprotokolle:/export/ --name "breitbandmessung" shneezin/breitbandmessung

cron_schedule = 0 */2 * * *     # Alle 2 Stunden```

```

To merge the csv files into one, run merge.sh or:

**Beispiele:**```

- `0 * * * *` = Jede Stundewget -O - https://raw.githubusercontent.com/shneezin/breitbandmessung/master/merge.sh | bash

- `0 8,20 * * *` = Um 8 und 20 Uhr```

- `*/30 * * * *` = Alle 30 Minuten

- `0 0 * * *` = Täglich um Mitternacht## New Features



### Einmalige Messung### Prometheus Support

The script now supports pushing metrics to Prometheus via a Pushgateway. Configure the `[prometheus]` section in your config.cfg:

Für einen einzelnen Test:- `gateway`: URL of your Prometheus Pushgateway

- `job`: Job name for the metrics (default: breitbandmessung)

```ini- `instance`: Instance identifier (default: default)

run_once = true

run_on_startup = true### Automatic Firefox Profile Cleanup

```The script now automatically cleans up Firefox profiles in `/tmp` after each run to prevent disk space issues that could accumulate over time.



Container stoppt nach der Messung automatisch.### Export Directory Creation

The script automatically creates the `/export` directory if it doesn't exist, ensuring measurement results are properly saved.

### Screenshots

### Fixed Cron Scheduling

```iniFixed issues with cron scheduling where escaped asterisks in the cron expression caused measurements to run every minute instead of the configured schedule.

[Settings]

save_screenshots = true## Configuration Examples

```

### Cron Schedule Examples

## 🛠️ Befehle- `0 */2 * * *` - Every 2 hours at minute 0

- `47 3 * * *` - Every day at 3:47 AM

```bash- `0 9,17 * * 1-5` - At 9:00 AM and 5:00 PM on weekdays

# Start

docker-compose up -d**Note**: Do not escape asterisks with backslashes in the cron configuration.



# StopThanks to shiaky for the idea on this project. 

docker-compose downYou can find his repo [here](https://github.com/shiaky/breitbandmessung)



# Logs ansehen## License

docker-compose logs -f

Feel free to use and improve the script as you like. I take no responsibility for the script.

# Neustart
docker-compose restart

# Status
docker-compose ps

# Manuelle Messung
docker-compose exec breitbandmessung /usr/src/app/speedtest.py

# Rebuild
docker-compose up -d --build
```

## 📋 Für Unraid

### Docker Compose Plugin

1. Installiere **Docker Compose Manager** aus Community Apps
2. Erstelle Stack mit `docker-compose.yml`
3. Setze `EXPORT_PATH=/mnt/user/data/breitbandmessung`
4. Start!

### Oder manuell via Terminal

```bash
cd /mnt/user/appdata/
git clone https://github.com/Serph91P/breitbandmessung.git
cd breitbandmessung

# Setze Export-Pfad
echo "EXPORT_PATH=/mnt/user/data/breitbandmessung" > .env

docker-compose up -d
```

## 🐛 Troubleshooting

### Container startet nicht

```bash
docker-compose logs
```

### Keine CSV-Dateien

Prüfe Volume-Mount:

```bash
docker-compose exec breitbandmessung ls -la /export
```

### Test manuell ausführen

```bash
docker-compose exec breitbandmessung /usr/src/app/speedtest.py
```

## 📝 Was wurde entfernt?

Diese Version ist **ultra-minimalistisch**:

- ❌ Keine Benachrichtigungen (Telegram, E-Mail, Twitter)
- ❌ Kein Monitoring (InfluxDB, Prometheus)
- ❌ Keine komplexen Dependencies (Rust, Cryptography)
- ✅ Nur das Nötigste: **Selenium + Firefox + CSV**

## 📊 CSV-Format

```csv
Datum;Zeit;Download (Mbit/s);Upload (Mbit/s);Laufzeit (ms);...
04.12.2025;10:30:00;52,5;12,3;15;...
```

## 📄 Lizenz

MIT

---

**Minimalistisch. Funktional. Fertig.** 🎯
