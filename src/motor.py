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
    Initialisiert das PWM-Modul und stoppt aus sicherheit alle Motoren.
    """
    protokoll.info("PWM-Modul wird initialisiert!")
    pwm_modul.frequency = 50
    alle_motoren_stoppen()


def alle_motoren_stoppen() -> None:
    """
    Schaltet alle verwendeten PCA9685-Kanäle aus.
    """
    for kanal in range(8):
        pwm_modul.channels[kanal].duty_cycle = 0


# ── Motor-Zuordnung ─────────────────────────────────────────

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
