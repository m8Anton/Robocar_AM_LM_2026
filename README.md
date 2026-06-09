# Linienfolgender Roboter

Ein kleiner Roboter, der versucht, einer Linie zu folgen, ohne komplett die Orientierung zu verlieren.  
Gebaut mit **Raspberry Pi**, **PCA9685 PWM-Modul**, **GPIOZero** und drei Liniensensoren.

Aktuell verwendet der Roboter **keinen PID-Regler**, sondern eine einfache **Bang-Bang-Steuerung**.  
Heißt übersetzt: Er denkt nicht lange nach, sondern macht klare Ansagen.

```text
Mitte sieht Linie  → geradeaus
Links sieht Linie  → rechte Motoren an
Rechts sieht Linie → linke Motoren an
Keine Linie        → panisch in letzter bekannter Richtung suchen
```

---

## Inhaltsverzeichnis

- [Projektbeschreibung](#projektbeschreibung)
- [Hardware](#hardware)
- [Projektstruktur](#projektstruktur)
- [Sensorlogik](#sensorlogik)
- [Motorlogik](#motorlogik)
- [Code-Dateien](#code-dateien)
- [Installation](#installation)
- [Raspberry Pi vorbereiten](#raspberry-pi-vorbereiten)
- [Programm starten](#programm-starten)
- [Programm stoppen](#programm-stoppen)
- [Wichtige Einstellungen](#wichtige-einstellungen)
- [Debugging](#debugging)
- [Häufige Fehler](#häufige-fehler)
- [Nützliche Commands](#nützliche-commands)
- [GitHub Commands](#github-commands)
- [Hinweis](#hinweis)

---

## Projektbeschreibung

Dieses Projekt steuert einen kleinen Linienfolger-Roboter.

Der Roboter fährt mit einer einfachen Logik:

| Sensorzustand | Aktion |
|---|---|
| Mitte aktiv | Geradeaus fahren |
| Links aktiv | Rechte Motoren fahren |
| Rechts aktiv | Linke Motoren fahren |
| Kein Sensor aktiv | Linie in letzter bekannter Richtung suchen |
| Links und rechts aktiv | Geradeaus fahren, weil eventuell Kreuzung oder breite Linie |

Das Ganze ist bewusst simpel gehalten.  
Der Roboter ist also eher **„mach einfach“**

---

## Hardware

Verwendete Hardware:

- Raspberry Pi
- PCA9685 PWM-Modul
- 3x Liniensensoren
- 4x DC-Motoren
- Motortreiber / Motormodule
- Externe Stromversorgung für die Motoren
- Gemeinsame Masseverbindung zwischen Raspberry Pi, PCA9685 und Motortreiber

Wichtig: Ohne gemeinsame Masse macht die Elektronik gerne Dinge, die niemand bestellt hat.

---

## Projektstruktur

```text
.
├── main.py
├── motor.py
├── sensor.py
├── car_controll.py
└── README.md
```

### `main.py`

Startet das Programm.  
Kurz gesagt: Der rote Startknopf, nur als Python-Datei.

### `motor.py`

Enthält die komplette Motorsteuerung über das PCA9685-Modul.  
Hier wird entschieden, welcher Motor bei welchem PWM-Kanal hängt.

### `sensor.py`

Liest die drei Liniensensoren aus.  
Die Sensoren sagen dem Roboter, ob er noch auf Kurs ist oder ob er das Steuerrad drehen soll.

### `car_controll.py`

Enthält die eigentliche Fahrlogik.  
Hier wird entschieden, ob der Roboter geradeaus fährt, korrigiert oder die Linie sucht.

---

## Sensorlogik

Die drei Sensoren sind so angeschlossen:

| Sensor | GPIO |
|---|---|
| Links | GPIO 14 |
| Mitte | GPIO 15 |
| Rechts | GPIO 23 |

Die Sensorwerte werden im Code als `0` oder `1` verarbeitet.

```text
1 = sieht Linie
0 = sieht keine Linie
```

Falls die Sensoren genau andersherum reagieren, kannst du das in `sensor.py` ändern:

```python
SENSOR_AKTIV_BEDEUTET_KEINE_LINIE = False
```

Auf `True` setzen, wenn `sensor.is_active` bedeutet, dass der Sensor **keine Linie** sieht:

```python
SENSOR_AKTIV_BEDEUTET_KEINE_LINIE = True
```

Merksatz:

```text
Wenn der Roboter genau das Gegenteil macht, ist höchst wahrscheinlich diese Einstellung schuld. Tut mir Leid, ist kein fehler sondern nh Feature.
```

---

## Motorlogik

Die Motoren werden über das PCA9685-Modul gesteuert.

Aktuelle Kanal-Zuordnung:

| Motor | PCA9685-Kanäle |
|---|---|
| Hinten links | 0 und 1 |
| Vorne links | 2 und 3 |
| Vorne rechts | 4 und 5 |
| Hinten rechts | 6 und 7 |

Die Motorsteuerung verwendet eine Panzersteuerung:

```text
linke Geschwindigkeit  = komplette linke Fahrzeugseite
rechte Geschwindigkeit = komplette rechte Fahrzeugseite
```

Beispiele:

```python
fahren(25, 25)
```

Roboter fährt geradeaus.

```python
fahren(25, 0)
```

Nur die linke Motorseite fährt.

```python
fahren(0, 25)
```

Nur die rechte Motorseite fährt.

Falls bei „rechte Motoren“ links etwas fährt, Profi TIPP: Dann ist wahrscheinlich nur die Seitenzuordnung in `motor.py` vertauscht.

---

## Code-Dateien

### `main.py`

```python
import logging

from motor import initialisieren
from car_controll import linie_folgen

logging.basicConfig(level=logging.INFO)


def hauptprogramm() -> None:
    """
    Startet das Roboterprogramm.
    """
    initialisieren()
    linie_folgen(dauer=60)


if __name__ == "__main__":
    hauptprogramm()
```

---

### `motor.py`

```python
import board
from adafruit_pca9685 import PCA9685
import logging

protokoll = logging.getLogger(__name__)

# ── PWM-Hardware ────────────────────────────────────────────
i2c = board.I2C()
pwm_modul = PCA9685(i2c)


# ── Hilfsfunktionen ─────────────────────────────────────────
def begrenzen(wert: float, minimum: float, maximum: float) -> float:
    """
    Begrenzt einen Wert auf einen erlaubten Bereich.
    """
    return max(minimum, min(maximum, wert))


def geschwindigkeit_zu_pwm(geschwindigkeit: float) -> int:
    """
    Wandelt eine Geschwindigkeit von 0 bis 100 Prozent
    in einen PWM-Wert von 0 bis 65535 um.
    """
    return int((abs(geschwindigkeit) * 0xFFFF) / 100)


def motor_setzen(kanal_vorwaerts: int, kanal_rueckwaerts: int, geschwindigkeit: float) -> None:
    """
    Steuert einen Motor über zwei PCA9685-Kanäle.

    Positive Geschwindigkeit  → Motor dreht vorwärts
    Negative Geschwindigkeit  → Motor dreht rückwärts
    Geschwindigkeit = 0       → Motor steht
    """
    geschwindigkeit = begrenzen(geschwindigkeit, -100, 100)
    pwm_wert = geschwindigkeit_zu_pwm(geschwindigkeit)

    if geschwindigkeit >= 0:
        pwm_modul.channels[kanal_vorwaerts].duty_cycle = 0
        pwm_modul.channels[kanal_rueckwaerts].duty_cycle = pwm_wert
    else:
        pwm_modul.channels[kanal_vorwaerts].duty_cycle = pwm_wert
        pwm_modul.channels[kanal_rueckwaerts].duty_cycle = 0


def initialisieren() -> None:
    """
    Initialisiert das PWM-Modul und stoppt sicherheitshalber alle Motoren.
    """
    protokoll.info("PWM-Modul wird initialisiert")
    pwm_modul.frequency = 50
    alle_motoren_stoppen()


def alle_motoren_stoppen() -> None:
    """
    Schaltet alle verwendeten PCA9685-Kanäle aus.
    """
    for kanal in range(8):
        pwm_modul.channels[kanal].duty_cycle = 0


# ── Motor-Zuordnung ─────────────────────────────────────────
# Diese Zuordnung basiert auf dem ursprünglichen Code.
# Wichtig: Wenn geradeaus_fahren() geradeaus fährt, passt diese Zuordnung.

def motor_vorne_links_setzen(geschwindigkeit: float) -> None:
    """
    Steuert den Motor vorne links.
    """
    motor_setzen(2, 3, -geschwindigkeit)


def motor_vorne_rechts_setzen(geschwindigkeit: float) -> None:
    """
    Steuert den Motor vorne rechts.
    """
    motor_setzen(4, 5, geschwindigkeit)


def motor_hinten_links_setzen(geschwindigkeit: float) -> None:
    """
    Steuert den Motor hinten links.
    """
    motor_setzen(0, 1, geschwindigkeit)


def motor_hinten_rechts_setzen(geschwindigkeit: float) -> None:
    """
    Steuert den Motor hinten rechts.
    """
    motor_setzen(6, 7, -geschwindigkeit)


def fahren(linke_geschwindigkeit: float, rechte_geschwindigkeit: float) -> None:
    """
    Panzersteuerung:

    linke_geschwindigkeit  = komplette linke Fahrzeugseite
    rechte_geschwindigkeit = komplette rechte Fahrzeugseite
    """
    motor_vorne_links_setzen(linke_geschwindigkeit)
    motor_hinten_links_setzen(linke_geschwindigkeit)

    motor_vorne_rechts_setzen(rechte_geschwindigkeit)
    motor_hinten_rechts_setzen(rechte_geschwindigkeit)
```

---

### `sensor.py`

```python
from gpiozero import LineSensor

# ── Sensor-Hardware ─────────────────────────────────────────
sensor_mitte = LineSensor(15)
sensor_links = LineSensor(14)
sensor_rechts = LineSensor(23)

# Sensorlogik:
# False = sensor.is_active bedeutet: Sensor sieht Linie
# True  = sensor.is_active bedeutet: Sensor sieht KEINE Linie
SENSOR_AKTIV_BEDEUTET_KEINE_LINIE = False


def sensor_sieht_linie(sensor: LineSensor) -> int:
    """
    Gibt 1 zurück, wenn der Sensor die Linie sieht.
    Gibt 0 zurück, wenn der Sensor die Linie nicht sieht.

    Die Konstante SENSOR_AKTIV_BEDEUTET_KEINE_LINIE kann die Logik umdrehen.
    """
    rohwert = bool(sensor.is_active)

    if SENSOR_AKTIV_BEDEUTET_KEINE_LINIE:
        return int(not rohwert)

    return int(rohwert)


def liniensensoren_lesen() -> tuple[int, int, int]:
    """
    Liest alle drei Liniensensoren aus.

    Rückgabe:
    links, mitte, rechts

    Beispiel:
    0, 1, 0 bedeutet:
    Nur der mittlere Sensor sieht die Linie.
    """
    links = sensor_sieht_linie(sensor_links)
    mitte = sensor_sieht_linie(sensor_mitte)
    rechts = sensor_sieht_linie(sensor_rechts)

    return links, mitte, rechts
```

---

### `car_controll.py`

```python
import time
import logging

from motor import fahren, alle_motoren_stoppen
from sensor import liniensensoren_lesen

protokoll = logging.getLogger(__name__)

# ── Einstellungen ───────────────────────────────────────────
GRUND_GESCHWINDIGKEIT = 25
DREH_GESCHWINDIGKEIT = 30
SUCH_GESCHWINDIGKEIT = 25


# ── Direkte Fahrfunktionen ──────────────────────────────────
def geradeaus_fahren() -> None:
    """
    Alle Motoren fahren mit gleicher Geschwindigkeit.
    Der Roboter fährt geradeaus.
    """
    fahren(GRUND_GESCHWINDIGKEIT, GRUND_GESCHWINDIGKEIT)


def linke_motoren_an() -> None:
    """
    Nur die linke Motorseite fährt.
    Die rechte Motorseite steht.
    """
    fahren(DREH_GESCHWINDIGKEIT, 0)


def rechte_motoren_an() -> None:
    """
    Nur die rechte Motorseite fährt.
    Die linke Motorseite steht.
    """
    fahren(0, DREH_GESCHWINDIGKEIT)


def linke_motoren_suche() -> None:
    """
    Nur die linke Motorseite fährt langsam beim Suchen der Linie.
    """
    fahren(SUCH_GESCHWINDIGKEIT, 0)


def rechte_motoren_suche() -> None:
    """
    Nur die rechte Motorseite fährt langsam beim Suchen der Linie.
    """
    fahren(0, SUCH_GESCHWINDIGKEIT)


# ── Bang-Bang-Linienfolger ──────────────────────────────────
def linie_folgen(dauer: float = 60) -> None:
    """
    Einfache Bang-Bang-Steuerung für den Linienfolger.

    Logik:
    Mitte sieht Linie      → geradeaus fahren
    Links sieht Linie      → rechte Motoren an
    Rechts sieht Linie     → linke Motoren an
    Keine Linie sichtbar   → in der letzten bekannten Richtung weitersuchen
    """
    startzeit = time.monotonic()

    # letzte_position:
    # -1 = linker Sensor war zuletzt aktiv
    #  0 = mittlerer Sensor war zuletzt aktiv
    #  1 = rechter Sensor war zuletzt aktiv
    letzte_position = 0

    protokoll.info("Bang-Bang-Linienfolger gestartet")

    try:
        while (time.monotonic() - startzeit) < dauer:
            links, mitte, rechts = liniensensoren_lesen()

            aktion = ""

            if mitte == 1:
                geradeaus_fahren()
                letzte_position = 0
                aktion = "GERADEAUS"

            elif links == 1 and rechts == 0:
                rechte_motoren_an()
                letzte_position = -1
                aktion = "RECHTE MOTOREN AN, weil LINKS aktiv"

            elif rechts == 1 and links == 0:
                linke_motoren_an()
                letzte_position = 1
                aktion = "LINKE MOTOREN AN, weil RECHTS aktiv"

            elif links == 1 and rechts == 1:
                geradeaus_fahren()
                aktion = "GERADEAUS, breite Linie oder Kreuzung"

            else:
                if letzte_position == -1:
                    rechte_motoren_suche()
                    aktion = "SUCHE: RECHTE MOTOREN, weil zuletzt LINKS aktiv"

                elif letzte_position == 1:
                    linke_motoren_suche()
                    aktion = "SUCHE: LINKE MOTOREN, weil zuletzt RECHTS aktiv"

                else:
                    rechte_motoren_suche()
                    aktion = "SUCHE STANDARD: RECHTE MOTOREN"

            print(f"Links={links} Mitte={mitte} Rechts={rechts} | {aktion}")

            time.sleep(0.03)

    except KeyboardInterrupt:
        protokoll.info("Abbruch durch Nutzer")

    finally:
        alle_motoren_stoppen()
        protokoll.info("Motoren gestoppt")
```

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/DEIN-NAME/DEIN-REPOSITORY.git
cd DEIN-REPOSITORY
```

Beispiel:

```bash
git clone https://github.com/dein-name/linienfolger-roboter.git
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

```text
Interface Options
I2C
Enable
```

Danach den Raspberry Pi neu starten:

```bash
sudo reboot
```

---

## I2C prüfen

Installiere die I2C-Tools:

```bash
sudo apt update
sudo apt install -y i2c-tools
```

Prüfe, ob das PCA9685-Modul erkannt wird:

```bash
i2cdetect -y 1
```

Normalerweise sollte eine Adresse wie diese angezeigt werden:

```text
40
```

Wenn keine Adresse angezeigt wird, überprüfe:

- SDA/SCL-Verkabelung
- Stromversorgung
- GND-Verbindung
- I2C-Aktivierung in `raspi-config`
- Ob das Modul überhaupt wach ist oder es schlafen geht wie ich gleich.

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
Betonung auf **versuchen**.

---

## Programm stoppen

Das Programm kann mit folgender Tastenkombination gestoppt werden:

```text
CTRL + C
```

Beim Stoppen werden alle Motoren automatisch ausgeschaltet.

Das ist wichtig, weil ein Roboter ohne Stop-Funktion einfach ein sehr kleines, sehr entschlossenes Problem ist.

---

## Wichtige Einstellungen

Die wichtigsten Geschwindigkeiten befinden sich in `car_controll.py`:

```python
GRUND_GESCHWINDIGKEIT = 25
DREH_GESCHWINDIGKEIT = 30
SUCH_GESCHWINDIGKEIT = 25
```

Bedeutung:

| Variable | Bedeutung |
|---|---|
| `GRUND_GESCHWINDIGKEIT` | Geschwindigkeit beim Geradeausfahren |
| `DREH_GESCHWINDIGKEIT` | Geschwindigkeit beim Korrigieren |
| `SUCH_GESCHWINDIGKEIT` | Geschwindigkeit beim Suchen der Linie |

Wenn der Roboter zu schnell ist:

```text
Werte kleiner machen.
```

Wenn der Roboter zu schwach korrigiert:

```text
DREH_GESCHWINDIGKEIT erhöhen.
```

Wenn der Roboter komplett eskaliert:

```text
Erst Strom aus, dann nachdenken.
```

---

## Debugging

Während das Programm läuft, werden die Sensorwerte ausgegeben:

```text
Links=0 Mitte=1 Rechts=0 | GERADEAUS
Links=1 Mitte=0 Rechts=0 | RECHTE MOTOREN AN, weil LINKS aktiv
Links=0 Mitte=0 Rechts=1 | LINKE MOTOREN AN, weil RECHTS aktiv
```

Damit kann geprüft werden:

- ob die Sensoren richtig erkannt werden
- ob die richtige Fahraktion ausgeführt wird
- ob die Motorseiten korrekt zugeordnet sind
- ob der Roboter wirklich dumm ist oder nur falsch verkabelt

---

## Häufige Fehler

### Import `board` nicht gefunden

Installiere Adafruit Blinka:

```bash
python3 -m pip install adafruit-blinka
```

---

### Import `adafruit_pca9685` nicht gefunden

Installiere die PCA9685-Bibliothek:

```bash
python3 -m pip install adafruit-circuitpython-pca9685
```

---

### Import `gpiozero` nicht gefunden

Installiere GPIOZero:

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

Prüfen:

```bash
i2cdetect -y 1
```

Falls keine Adresse angezeigt wird:

- I2C aktivieren
- Verkabelung prüfen
- SDA und SCL prüfen
- GND verbinden
- Stromversorgung prüfen
- Verbindung nicht nur anschauen, sondern wirklich prüfen

---

### Rechte Motoren sollen fahren, aber linke Motoren fahren

Dann ist die Seitenzuordnung in `motor.py` vertauscht.

Aktuelle Funktion:

```python
def fahren(linke_geschwindigkeit: float, rechte_geschwindigkeit: float) -> None:
    motor_vorne_links_setzen(linke_geschwindigkeit)
    motor_hinten_links_setzen(linke_geschwindigkeit)

    motor_vorne_rechts_setzen(rechte_geschwindigkeit)
    motor_hinten_rechts_setzen(rechte_geschwindigkeit)
```

Zum Tauschen der Seiten:

```python
def fahren(linke_geschwindigkeit: float, rechte_geschwindigkeit: float) -> None:
    motor_vorne_links_setzen(rechte_geschwindigkeit)
    motor_hinten_links_setzen(rechte_geschwindigkeit)

    motor_vorne_rechts_setzen(linke_geschwindigkeit)
    motor_hinten_rechts_setzen(linke_geschwindigkeit)
```

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
git commit -m "Linienfolger Roboter hinzugefügt"
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

## README auf dem Raspberry Pi erstellen

Datei öffnen:

```bash
nano README.md
```

Inhalt einfügen.

Speichern:

```text
CTRL + O
ENTER
CTRL + X
```

Danach zu GitHub hinzufügen:

```bash
git add README.md
git commit -m "README hinzugefügt"
git push
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
