# Linienfolgender Roboter

Ein kleiner Roboter, der versucht, einer Linie zu folgen, ohne komplett die Orientierung zu verlieren.  
Gebaut mit Raspberry Pi, PCA9685 PWM-Modul, GPIOZero und drei Liniensensoren.

Aktuell verwendet der Roboter einen **proportionalen Regler (P-Regler)**.  
Das heißt: Je länger er falsch fährt, desto mehr steuert er gegen.  
Kein PID. Kein Bang-Bang. Einfach P — und das reicht meistens.

```
Mitte sieht Linie              → geradeaus  
Mitte + Links sieht Linie      → leicht nach links korrigieren  
Mitte + Rechts sieht Linie     → leicht nach rechts korrigieren  
Nur Links sieht Linie          → stark nach links korrigieren (steigt mit der Zeit)  
Nur Rechts sieht Linie         → stark nach rechts korrigieren (steigt mit der Zeit)  
Links + Rechts sehen Linie     → geradeaus (Kreuzung oder breite Linie)  
Keine Linie                    → panisch in letzter bekannter Richtung suchen
```

---

## Inhaltsverzeichnis

- [Projektbeschreibung](#projektbeschreibung)
- [Hardware](#hardware)
- [Projektstruktur](#projektstruktur)
- [Sensorlogik](#sensorlogik)
- [Motorlogik](#motorlogik)
- [Regler-Logik](#regler-logik)
- [Wichtige Einstellungen](#wichtige-einstellungen)
- [Installation](#installation)
- [Raspberry Pi vorbereiten](#raspberry-pi-vorbereiten)
- [Programm starten](#programm-starten)
- [Programm stoppen](#programm-stoppen)
- [Debugging](#debugging)
- [Häufige Fehler](#häufige-fehler)
- [Nützliche Commands](#nützliche-commands)
- [GitHub Commands](#github-commands)
- [Hinweis](#hinweis)

---

## Projektbeschreibung

Dieses Projekt steuert einen kleinen Linienfolger-Roboter mit einem proportionalen Regler.

Der Roboter fährt mit folgender Logik:

| Sensorzustand | Aktion |
|---|---|
| Nur Mitte aktiv | Geradeaus fahren |
| Mitte + Links aktiv | Leicht nach links korrigieren |
| Mitte + Rechts aktiv | Leicht nach rechts korrigieren |
| Nur Links aktiv | Nach links korrigieren (Korrektur steigt mit der Zeit) |
| Nur Rechts aktiv | Nach rechts korrigieren (Korrektur steigt mit der Zeit) |
| Links + Rechts aktiv | Geradeaus fahren — wahrscheinlich Kreuzung oder breite Linie |
| Kein Sensor aktiv | Linie in letzter bekannter Richtung suchen |

Das Ganze ist proportional geregelt: Je länger der Roboter falsch fährt, desto aggressiver korrigiert er.  
Und ja, er kann auch rückwärts fahren. Features, keine Bugs.

---

## Hardware

Verwendete Hardware:

- Raspberry Pi
- PCA9685 PWM-Modul
- 3x Liniensensoren
- 4x DC-Motoren
- Motortreiber / Motormodule
- Gemeinsame Masseverbindung zwischen Raspberry Pi, PCA9685 und Motortreiber

**Wichtig:** Ohne gemeinsame Masse macht die Elektronik gerne Dinge, die niemand bestellt hat.

---

## Projektstruktur

```
.  
├── main.py  
├── motor.py  
├── sensor.py  
├── car_control.py  
└── README.md
```

### main.py

Startet das Programm.  
Kurz gesagt: Der rote Startknopf, nur als Python-Datei.

### motor.py

Enthält die komplette Motorsteuerung über das PCA9685-Modul.  
Hier wird entschieden, welcher Motor bei welchem PWM-Kanal hängt.

### sensor.py

Liest die drei Liniensensoren aus.  
Die Sensoren sagen dem Roboter, ob er noch auf Kurs ist oder ob er das Steuerrad drehen soll.

### car_control.py

Enthält die eigentliche Fahrlogik mit dem proportionalen Regler.  
Hier wird entschieden, wie stark korrigiert wird — und die Antwort ist: immer stärker, bis er wieder auf der Linie ist.

---

## Sensorlogik

Die drei Sensoren sind so angeschlossen:

| Sensor | GPIO |
|---|---|
| Links | GPIO 14 |
| Mitte | GPIO 15 |
| Rechts | GPIO 23 |

Die Sensorwerte werden im Code als `0` oder `1` verarbeitet.

```
1 = sieht Linie  
0 = sieht keine Linie
```

Falls die Sensoren genau andersherum reagieren, kann das in `sensor.py` geändert werden:

```python
SENSOR_AKTIV_BEDEUTET_KEINE_LINIE = False
```

Auf `True` setzen, wenn `sensor.is_active` bedeutet, dass der Sensor **keine** Linie sieht:

```python
SENSOR_AKTIV_BEDEUTET_KEINE_LINIE = True
```

**Merksatz:**  
Wenn der Roboter genau das Gegenteil macht, ist höchstwahrscheinlich diese Einstellung schuld.  
Tut mir leid, ist kein Fehler, sondern ein Feature.

---

## Motorlogik

Die Motoren werden über das PCA9685-Modul gesteuert.

**Aktuelle Kanal-Zuordnung:**

| Motor | PCA9685-Kanäle |
|---|---|
| Hinten links | 0 und 1 |
| Vorne links | 2 und 3 |
| Vorne rechts | 4 und 5 |
| Hinten rechts | 6 und 7 |

Die Motorsteuerung verwendet eine **Panzersteuerung**:

```
linke Geschwindigkeit  = komplette linke Fahrzeugseite  
rechte Geschwindigkeit = komplette rechte Fahrzeugseite
```

**Beispiele:**

```python
fahren(35, 35)   # Roboter fährt geradeaus
fahren(35, 10)   # Roboter dreht leicht nach rechts
fahren(-20, 35)  # Linke Seite rückwärts, rechts vorwärts → scharfe Linkskurve
```

Ja, negative Werte sind möglich. Der Roboter kann also rückwärts drehen, wenn die Kurve es verlangt.  
Falls bei „rechte Motoren" links etwas fährt: Dann ist wahrscheinlich nur die Seitenzuordnung in `motor.py` vertauscht.

---

## Regler-Logik

Der P-Regler in `car_control.py` funktioniert so:

**Korrektur steigt mit der Zeit:**  
Je länger der Roboter von der Linie abweicht, desto stärker wird gegensteuert.  
Startet mit `KORREKTUR_START` und steigt pro Sekunde um `KORREKTUR_ANSTIEG_PRO_SEKUNDE`.

**Gnadenfrist:**  
Wenn der Roboter gerade eben erst von der Mitte weggekommen ist (`GERADE_TOLERANZ`), wird nur sanft korrigiert.  
Damit er nicht bei jeder kleinen Kurve sofort ausrastet.

**Rückwärtsfahren:**  
Bei sehr starker Korrektur kann die Innenseite auch rückwärts fahren (`MINDEST_GESCHWINDIGKEIT_RUECKWAERTS`).  
Das hilft bei engen Kurven. Features, keine Bugs.

---

## Wichtige Einstellungen

Alle relevanten Werte befinden sich in `car_control.py`:

```python
GRUND_GESCHWINDIGKEIT           = 35   # Grundgeschwindigkeit vorwärts
MIN_MOTOR                       = -25  # Maximale Rückwärtsgeschwindigkeit
MAX_MOTOR                       = 45   # Maximale Vorwärtsgeschwindigkeit

KORREKTUR_GERADE                = 8    # Kleine Korrektur wenn fast mittig
KORREKTUR_START                 = 5    # Startkorrektur beim Erkennen einer Kurve
KORREKTUR_MAX                   = 35   # Maximale Korrektur (ab hier dreht er fast auf der Stelle)
KORREKTUR_ANSTIEG_PRO_SEKUNDE   = 12   # Wie schnell die Korrektur wächst
KORREKTUR_FAST_MITTE            = 8    # Korrektur wenn Mitte + eine Seite aktiv

GERADE_TOLERANZ                 = 0.3  # Sekunden Gnadenfrist nach Mitte
REGEL_PAUSE                     = 0.009  # Pause pro Regelschleife
SICHERHEITS_DAUER               = 60   # Maximale Laufzeit in Sekunden
MINDEST_GESCHWINDIGKEIT_RUECKWAERTS = -20  # Grenze für Rückwärtsfahren
```

**Bedeutung der wichtigsten Werte:**

| Variable | Bedeutung |
|---|---|
| `GRUND_GESCHWINDIGKEIT` | Geschwindigkeit beim Geradeausfahren |
| `KORREKTUR_MAX` | Maximale Korrekturstärke — ab hier dreht er fast auf der Stelle |
| `KORREKTUR_ANSTIEG_PRO_SEKUNDE` | Wie aggressiv die Korrektur mit der Zeit wächst |
| `GERADE_TOLERANZ` | Kurze Gnadenfrist nach Mitte, bevor stark korrigiert wird |
| `MIN_MOTOR` | Wie weit eine Motorseite rückwärts darf |

**Wenn der Roboter zu schnell ist:**  
`GRUND_GESCHWINDIGKEIT` und `MAX_MOTOR` kleiner machen.

**Wenn der Roboter bei Kurven zu langsam reagiert:**  
`KORREKTUR_ANSTIEG_PRO_SEKUNDE` erhöhen.

**Wenn der Roboter bei jeder kleinen Kurve übersteuert:**  
`KORREKTUR_ANSTIEG_PRO_SEKUNDE` verkleinern oder `GERADE_TOLERANZ` erhöhen.

**Wenn der Roboter komplett eskaliert:**  
Erst Strom aus, dann nachdenken.

**Wenn ihr mein Code anschaut,merkt ihr eine Einstellung die Wenig Sinn macht**
Die Rechten Motoren drehen schneller als die Linken.

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/m8Anton/Robocar_AM_LM_2026
cd DEIN-REPOSITORY
```

Beispiel:

```bash
git clone 
https://github.com/m8Anton/Robocar_AM_LM_2026
cd linienfolger-roboter
```

---

### 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
```

Virtuelle Umgebung aktivieren:

```bash
source .venv/bin/activate
```

---

### 3. Pakete installieren

```bash
python3 -m pip install --upgrade pip
python3 -m pip install adafruit-blinka adafruit-circuitpython-pca9685 gpiozero
```

---

## Raspberry Pi vorbereiten

Das PCA9685-Modul verwendet I2C.  
Deshalb muss I2C auf dem Raspberry Pi aktiviert werden.

```bash
sudo raspi-config
```

Dann auswählen:

```
Interface Options  
I2C  
Enable
```

Danach den Raspberry Pi neu starten:

```bash
sudo reboot
```

---

### I2C prüfen

I2C-Tools installieren:

```bash
sudo apt update
sudo apt install -y i2c-tools
```

Prüfen, ob das PCA9685-Modul erkannt wird:

```bash
i2cdetect -y 1
```

Normalerweise sollte eine Adresse wie diese angezeigt werden:

```
40
```

Wenn keine Adresse angezeigt wird, überprüfe:

- SDA/SCL-Verkabelung
- Stromversorgung
- GND-Verbindung
- I2C-Aktivierung in `raspi-config`
- Ob das Modul überhaupt wach ist oder es schlafen geht wie ich gleich

---

## Programm starten

Virtuelle Umgebung aktivieren:

```bash
source .venv/bin/activate
```

Programm starten:

```bash
python3 main.py
```

Dann sollte der Roboter versuchen, der Linie zu folgen.  
Betonung auf versuchen.

---

## Programm stoppen

Das Programm kann mit folgender Tastenkombination gestoppt werden:

```
CTRL + C
```

Beim Stoppen werden alle Motoren automatisch ausgeschaltet.

Das ist wichtig, weil ein Roboter ohne Stop-Funktion einfach ein sehr kleines, sehr entschlossenes Problem ist.

---

## Debugging

Während das Programm läuft, werden die Sensorwerte und die aktuelle Aktion ausgegeben:

```
Links=0 Mitte=1 Rechts=0 | GERADEAUS
Links=1 Mitte=0 Rechts=0 | LINKS KORRIGIEREN | Korrektur=17
Links=0 Mitte=0 Rechts=1 | RECHTS KORRIGIEREN | Korrektur=29
Links=0 Mitte=1 Rechts=1 | LEICHT RECHTS | Korrektur=8
Links=0 Mitte=0 Rechts=0 | SUCHE RECHTS | Korrektur=35
```

Damit kann geprüft werden:

- ob die Sensoren richtig erkannt werden
- ob die richtige Fahraktion ausgeführt wird
- wie groß die aktuelle Korrektur ist
- ob der Roboter wirklich dumm ist oder nur falsch verkabelt

---

## Häufige Fehler

### `Import board` nicht gefunden

```bash
python3 -m pip install adafruit-blinka
```

---

### `Import adafruit_pca9685` nicht gefunden

```bash
python3 -m pip install adafruit-circuitpython-pca9685
```

---

### `Import gpiozero` nicht gefunden

```bash
python3 -m pip install gpiozero
```

---

### Alle Imports testen

```bash
python3 -c "import board; from adafruit_pca9685 import PCA9685; import gpiozero; print('Alle Imports funktionieren')"
```

Wenn das funktioniert, ist Python zumindest nicht das Problem.  
Dann bleibt nur noch Hardware. Also das Lustige.

---

### PCA9685 wird nicht erkannt

```bash
i2cdetect -y 1
```

Falls keine Adresse angezeigt wird:

- I2C aktivieren
- SDA und SCL prüfen
- GND verbinden
- Stromversorgung prüfen
- Verbindung nicht nur anschauen, sondern wirklich prüfen

---

### Rechte Motoren sollen fahren, aber linke Motoren fahren

Dann ist die Seitenzuordnung in `motor.py` vertauscht.

Zum Tauschen der Seiten:

```python
def fahren(linke_geschwindigkeit: float, rechte_geschwindigkeit: float) -> None:
    motor_vorne_links_setzen(rechte_geschwindigkeit)
    motor_hinten_links_setzen(rechte_geschwindigkeit)

    motor_vorne_rechts_setzen(linke_geschwindigkeit)
    motor_hinten_rechts_setzen(linke_geschwindigkeit)
```

---

### Roboter dreht sich wild auf der Stelle

`KORREKTUR_MAX` ist wahrscheinlich zu hoch oder `KORREKTUR_ANSTIEG_PRO_SEKUNDE` zu groß.  
Werte schrittweise reduzieren, bis er sich benimmt.

---

### Roboter reagiert zu träge auf Kurven

`KORREKTUR_ANSTIEG_PRO_SEKUNDE` erhöhen oder `GERADE_TOLERANZ` verkleinern.

---

## Nützliche Commands

### Repository klonen

```bash
git clone https://github.com/DEIN-NAME/DEIN-REPOSITORY.git
cd DEIN-REPOSITORY
```

### Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
```

### Virtuelle Umgebung aktivieren

```bash
source .venv/bin/activate
```

### Pakete installieren

```bash
python3 -m pip install adafruit-blinka adafruit-circuitpython-pca9685 gpiozero
```

### Pakete aktualisieren

```bash
python3 -m pip install --upgrade adafruit-blinka adafruit-circuitpython-pca9685 gpiozero
```

### Programm starten

```bash
python3 main.py
```

### I2C prüfen

```bash
i2cdetect -y 1
```

### Python-Version prüfen

```bash
python3 --version
```

### Aktiven Python-Pfad anzeigen

```bash
which python3
```

### Installierte Pakete prüfen

```bash
python3 -m pip show adafruit-blinka
python3 -m pip show adafruit-circuitpython-pca9685
python3 -m pip show gpiozero
```

### Imports prüfen

```bash
python3 -c "import board; from adafruit_pca9685 import PCA9685; import gpiozero; print('Alle Imports funktionieren')"
```

---

## GitHub Commands

### Git-Status anzeigen

```bash
git status
```

### Alle Änderungen hinzufügen

```bash
git add .
```

### Commit erstellen

```bash
git commit -m "P-Regler Linienfolger"
```

### Änderungen hochladen

```bash
git push
```

Falls der Branch `main` noch nicht existiert oder neu gesetzt werden muss:

```bash
git branch -M main
git push -u origin main
```

---

## Hinweis

Der Code ist für einen Raspberry Pi gedacht.

Auf Windows kann der Code bearbeitet werden, aber die GPIO- und I2C-Hardware funktioniert dort nicht direkt.

Das Programm sollte auf dem Raspberry Pi gestartet werden:

```bash
python3 main.py
```

---

## Lizenz

Dieses Projekt kann frei für Lern- und Schulprojekte verwendet werden.

Benutzung auf eigene Gefahr.  
Falls der Roboter gegen eine Wand fährt, war das vermutlich kein Bug, sondern ein Feature in Entwicklung.
