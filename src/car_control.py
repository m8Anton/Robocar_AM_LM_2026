import time
import logging

from motor import fahren, alle_motoren_stoppen
from sensor import liniensensoren_lesen

protokoll = logging.getLogger(__name__)


# ── Einstellungen ───────────────────────────────────────────

GRUND_GESCHWINDIGKEIT = 22
MIN_MOTOR = -30
MAX_MOTOR = 35
LOSFAHR_GESCHWINDIGKEIT = 20

# ── Korrektur-Einstellungen ─────────────────────────────────

KORREKTUR_GERADE = 5
KORREKTUR_START = 8
KORREKTUR_MAX = 40
KORREKTUR_ANSTIEG_PRO_SEKUNDE = 10
GERADE_TOLERANZ = 0.12
REGEL_PAUSE = 0.03
KORREKTUR_FAST_MITTE = 5

# ── Hilfsfunktionen ─────────────────────────────────────────

def begrenzen(wert: int, minimum: int, maximum: int) -> int:
    """
    Begrenzung für Motorwerte.
    """
    return max(minimum, min(maximum, wert))


def motoren_setzen(linker_motor: int, rechter_motor: int) -> None:
    """
    Setzt beide Motoren und begrenzt sie auf den erlaubten Bereich.
    """
    linker_motor = begrenzen(linker_motor, MIN_MOTOR, MAX_MOTOR)
    rechter_motor = begrenzen(rechter_motor, MIN_MOTOR, MAX_MOTOR)

    fahren(linker_motor, rechter_motor)


def geradeaus_fahren() -> None:
    """
    Beide Seiten fahren gleich schnell.
    """
    motoren_setzen(GRUND_GESCHWINDIGKEIT, GRUND_GESCHWINDIGKEIT)


def berechne_korrektur(
    kurven_startzeit: float | None,
    letzte_mitte_zeit: float
) -> int:
    """
    Berechnet die Korrektur abhängig davon,
    wie lange der Roboter schon in einer Kurve ist.

    Direkt nach mittigem Linienkontakt wird nur weich korrigiert.
    Dadurch pendelt der Roboter auf Geraden weniger.
    """
    jetzt = time.monotonic()

    # Wenn der Roboter gerade eben noch mittig war,
    # nur leicht korrigieren.
    if (jetzt - letzte_mitte_zeit) < GERADE_TOLERANZ:
        return KORREKTUR_GERADE

    # Falls noch keine Kurvenzeit gesetzt ist,
    # mit der Startkorrektur beginnen.
    if kurven_startzeit is None:
        return KORREKTUR_START

    kurven_dauer = jetzt - kurven_startzeit

    korrektur = (
        KORREKTUR_START
        + kurven_dauer * KORREKTUR_ANSTIEG_PRO_SEKUNDE
    )

    return min(int(korrektur), KORREKTUR_MAX)


def nach_links_korrigieren(korrektur: int) -> None:
    """
    Der Roboter korrigiert nach links.

    Linke Seite wird langsamer.
    Rechte Seite wird schneller.

    Bei großer Korrektur kann die linke Seite negativ werden.
    """
    linker_motor = GRUND_GESCHWINDIGKEIT - korrektur * 2
    rechter_motor = GRUND_GESCHWINDIGKEIT + korrektur

    motoren_setzen(linker_motor, rechter_motor)


def nach_rechts_korrigieren(korrektur: int) -> None:
    """
    Der Roboter korrigiert nach rechts.

    Rechte Seite wird langsamer.
    Linke Seite wird schneller.

    Bei großer Korrektur kann die rechte Seite negativ werden.
    """
    linker_motor = GRUND_GESCHWINDIGKEIT + korrektur
    rechter_motor = GRUND_GESCHWINDIGKEIT - korrektur * 2

    motoren_setzen(linker_motor, rechter_motor)


# ── Linienfolger ────────────────────────────────────────────

def linie_folgen(dauer: float = 60) -> None:
    """
    Linienfolger mit weicher Korrektur auf Geraden
    und stärker werdender Korrektur in längeren Kurven.

    Sensorlogik:
    Mitte aktiv              → geradeaus
    Mitte + links aktiv      → leicht nach links korrigieren
    Mitte + rechts aktiv     → leicht nach rechts korrigieren
    Nur links aktiv          → stärker nach links korrigieren
    Nur rechts aktiv         → stärker nach rechts korrigieren
    Kein Sensor aktiv        → in letzter bekannter Richtung suchen
    Links + rechts aktiv     → Kreuzung/breite Linie, geradeaus
    """

    startzeit = time.monotonic()

    # -1 = Linie zuletzt links gesehen
    #  0 = Linie zuletzt mittig gesehen
    #  1 = Linie zuletzt rechts gesehen
    letzte_position = 0

    # Seit wann ist der Roboter in einer Kurve? Keine ahnung jetzt wissen wir es.
    kurven_startzeit = None

    # Aktuelle Kurvenrichtung:
    # -1 = links korrigieren
    #  0 = keine Kurve
    #  1 = rechts korrigieren
    aktuelle_kurvenrichtung = 0

    # Zeitpunkt, wann der mittlere Sensor zuletzt aktiv war.
    letzte_mitte_zeit = time.monotonic()

    protokoll.info("Linienfolger gestartet")

    try:
        while (time.monotonic() - startzeit) < dauer:
            links, mitte, rechts = liniensensoren_lesen()
            jetzt = time.monotonic()

            aktion = ""

            # ── Genau mittig auf der Linie ───────────────────
            if mitte == 1 and links == 0 and rechts == 0:
                geradeaus_fahren()

                letzte_position = 0
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None
                letzte_mitte_zeit = jetzt

                aktion = "GERADEAUS"

            # ── Mitte und links sehen Linie ──────────────────
            # Fast mittig, nur leicht nach links korrigieren.
            elif mitte == 1 and links == 1 and rechts == 0:
                korrektur = KORREKTUR_GERADE
                nach_links_korrigieren(korrektur)

                letzte_position = -1
                letzte_mitte_zeit = jetzt
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None

                aktion = f"LEICHT LINKS | Korrektur={korrektur}"

            # ── Mitte und rechts sehen Linie ─────────────────
            # Fast mittig, nur leicht nach rechts korrigieren.
            elif mitte == 1 and rechts == 1 and links == 0:
                korrektur = KORREKTUR_FAST_MITTE
                nach_rechts_korrigieren(korrektur)

                letzte_position = 1
                letzte_mitte_zeit = jetzt
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None

                aktion = f"LEICHT RECHTS | Korrektur={korrektur}"

            # ── Nur links sieht Linie ────────────────────────
            # Linie ist links, also muss der Roboter nach links.
            elif links == 1 and mitte == 0 and rechts == 0:
                if aktuelle_kurvenrichtung != -1:
                    kurven_startzeit = jetzt
                    aktuelle_kurvenrichtung = -1

                korrektur = berechne_korrektur(
                    kurven_startzeit,
                    letzte_mitte_zeit
                )

                nach_links_korrigieren(korrektur)

                letzte_position = -1

                aktion = f"LINKS KORRIGIEREN | Korrektur={korrektur}"

            # ── Nur rechts sieht Linie ───────────────────────
            # Linie ist rechts, also muss der Roboter nach rechts.
            elif rechts == 1 and mitte == 0 and links == 0:
                if aktuelle_kurvenrichtung != 1:
                    kurven_startzeit = jetzt
                    aktuelle_kurvenrichtung = 1

                korrektur = berechne_korrektur(
                    kurven_startzeit,
                    letzte_mitte_zeit
                )

                nach_rechts_korrigieren(korrektur)

                letzte_position = 1

                aktion = f"RECHTS KORRIGIEREN | Korrektur={korrektur}"

            # ── Links und rechts aktiv ───────────────────────
            # Kann breite Linie oder Kreuzung sein.
            elif links == 1 and rechts == 1:
                geradeaus_fahren()

                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None
                letzte_mitte_zeit = jetzt

                aktion = "GERADEAUS / KREUZUNG"

            # ── Keine Linie sichtbar ─────────────────────────
            else:
                # Wenn die Linie zuletzt links war,
                # weiter nach links suchen.
                if letzte_position == -1:
                    if aktuelle_kurvenrichtung != -1:
                        kurven_startzeit = jetzt
                        aktuelle_kurvenrichtung = -1

                    korrektur = berechne_korrektur(
                        kurven_startzeit,
                        letzte_mitte_zeit
                    )

                    nach_links_korrigieren(korrektur)

                    aktion = f"SUCHE LINKS | Korrektur={korrektur}"

                # Wenn die Linie zuletzt rechts war,
                # weiter nach rechts suchen.
                elif letzte_position == 1:
                    if aktuelle_kurvenrichtung != 1:
                        kurven_startzeit = jetzt
                        aktuelle_kurvenrichtung = 1

                    korrektur = berechne_korrektur(
                        kurven_startzeit,
                        letzte_mitte_zeit
                    )

                    nach_rechts_korrigieren(korrektur)

                    aktion = f"SUCHE RECHTS | Korrektur={korrektur}"

                # Wenn vorher Mitte aktiv war,
                # nur leicht suchen, nicht sofort stark drehen.
                else:
                    korrektur = KORREKTUR_GERADE
                    nach_links_korrigieren(korrektur)

                    aktuelle_kurvenrichtung = -1
                    kurven_startzeit = jetzt

                    aktion = f"SUCHE LEICHT LINKS | Korrektur={korrektur}"

            print(
                f"Links={links} Mitte={mitte} Rechts={rechts} | {aktion}"
            )

            time.sleep(REGEL_PAUSE)

    except KeyboardInterrupt:
        protokoll.info("Abbruch durch Nutzer")

    finally:
        alle_motoren_stoppen()
        protokoll.info("Motoren gestoppt")
