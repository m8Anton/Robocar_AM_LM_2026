import time
import logging

from motor import fahren, alle_motoren_stoppen
from sensor import liniensensoren_lesen

protokoll = logging.getLogger(__name__)


# ── Grundeinstellungen ──────────────────────────────────────
SICHERHEITS_DAUER = 60
MINDEST_GESCHWINDIGKEIT_RUECKWAERTS = -20
GRUND_GESCHWINDIGKEIT = 35      # nicht zu schnell, nicht zu langsam, perfekt (laut mir)
MIN_MOTOR = -25                  # ja, rückwärts geht auch.
MAX_MOTOR = 45                   # Begrenzung der Motorleistung

# ── Korrekturwerte ──────────────────────────────────────────

KORREKTUR_GERADE = 8             # kleine Korrektur, kaum merkbar
KORREKTUR_START = 5              # damit er nicht gleich am Anfang ausbricht
KORREKTUR_MAX = 35               # ab hier dreht er sich fast auf der Stelle
KORREKTUR_ANSTIEG_PRO_SEKUNDE = 12  # je länger er falsch fährt, desto mehr wird gegensteuert
GERADE_TOLERANZ = 0.3         # kurz nach Mitte noch sanft korrigieren (Gnadenfrist)
REGEL_PAUSE = 0.009               # kurze Pause, damit der Pi nicht abraucht
KORREKTUR_FAST_MITTE = 8        # fast mittig = fast richtig = fast gut genug

# ── Hilfsfunktionen ─────────────────────────────────────────

def begrenzen(wert: int, minimum: int, maximum: int) -> int:
    # Damit er nicht auf der Stelle dreht oder übersteuert
    return max(minimum, min(maximum, wert))


def motoren_setzen(linker_motor: int, rechter_motor: int) -> None:
    # Beide Motoren begrenzen und ansteuern
    # (ja, die Begrenzung ist nötig)
    linker_motor = begrenzen(linker_motor, MIN_MOTOR, MAX_MOTOR)
    rechter_motor = begrenzen(rechter_motor, MIN_MOTOR, MAX_MOTOR)
    fahren(linker_motor, rechter_motor)


def geradeaus_fahren() -> None:
    # Beide gleich schnell -> geradeaus. Rocket science.
    motoren_setzen(GRUND_GESCHWINDIGKEIT, GRUND_GESCHWINDIGKEIT)


def berechne_korrektur(kurven_startzeit: float | None,letzte_mitte_zeit: float) -> int:

    jetzt = time.monotonic()

    # Gerade eben noch mittig -> chillen, nicht sofort übersteuern
    if (jetzt - letzte_mitte_zeit) < GERADE_TOLERANZ:
        return KORREKTUR_GERADE

    # Kurve fängt gerade erst an, erstmal locker angehen
    if kurven_startzeit is None:
        return KORREKTUR_START

    kurven_dauer = jetzt - kurven_startzeit

    # Korrektur steigt mit der Zeit — Panik wächst exponentiell, Korrektur linear
    korrektur = KORREKTUR_START + kurven_dauer * KORREKTUR_ANSTIEG_PRO_SEKUNDE

    return min(int(korrektur), KORREKTUR_MAX)


def nach_links_korrigieren(korrektur: int) -> None:
    # Links abbremsen, rechts Gas geben -> dreht nach links
    # Bei sehr großer Korrektur fährt links rückwärts. Features, keine Bugs.
    linker_motor = max(MINDEST_GESCHWINDIGKEIT_RUECKWAERTS, -GRUND_GESCHWINDIGKEIT - korrektur)
    rechter_motor = GRUND_GESCHWINDIGKEIT + korrektur
    motoren_setzen(linker_motor, rechter_motor)


def nach_rechts_korrigieren(korrektur: int) -> None:
    # Rechts abbremsen, links Gas geben -> dreht nach rechts
    linker_motor = GRUND_GESCHWINDIGKEIT + korrektur
    rechter_motor = max(MINDEST_GESCHWINDIGKEIT_RUECKWAERTS, -GRUND_GESCHWINDIGKEIT - korrektur)
    motoren_setzen(linker_motor, rechter_motor)


# ── Linienfolger ────────────────────────────────────────────

def linie_folgen(dauer: float = SICHERHEITS_DAUER) -> None:

    startzeit = time.monotonic()

    # Letzte bekannte Position der Linie: -1 links, 0 mitte, 1 rechts
    letzte_position = 0

    # Ab wann die aktuelle Kurve angefangen hat
    kurven_startzeit = None

    # Wohin er gerade korrigiert: -1 links, 0 gar nicht, 1 rechts
    aktuelle_kurvenrichtung = 0

    # Wann der mittlere Sensor zuletzt was gesehen hat
    letzte_mitte_zeit = time.monotonic()

    protokoll.info("Linienfolger gestartet")

    try:
        while (time.monotonic() - startzeit) < dauer:
            links, mitte, rechts = liniensensoren_lesen()
            jetzt = time.monotonic()

            aktion = ""

            # ── Perfekt mittig — so soll's sein ─────────────
            if mitte == 1 and links == 0 and rechts == 0:
                geradeaus_fahren()

                letzte_position = 0
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None
                letzte_mitte_zeit = jetzt

                aktion = "GERADEAUS"

            # ── Mitte + links -> fast richtig, bisschen links ─
            elif mitte == 1 and links == 1 and rechts == 0:
                korrektur = KORREKTUR_GERADE
                nach_links_korrigieren(korrektur)

                letzte_position = -1
                letzte_mitte_zeit = jetzt
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None

                aktion = f"LEICHT LINKS | Korrektur={korrektur} "

            # ── Mitte + rechts -> fast richtig, bisschen rechts ─
            elif mitte == 1 and rechts == 1 and links == 0:
                korrektur = KORREKTUR_FAST_MITTE
                nach_rechts_korrigieren(korrektur)

                letzte_position = 1
                letzte_mitte_zeit = jetzt
                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None

                aktion = f"LEICHT RECHTS | Korrektur={korrektur}"

            # ── Nur links -> Linie ist links, Notfall links ───
            elif links == 1 and mitte == 0 and rechts == 0:
                if aktuelle_kurvenrichtung != -1:
                    kurven_startzeit = jetzt
                    aktuelle_kurvenrichtung = -1

                korrektur = berechne_korrektur(kurven_startzeit, letzte_mitte_zeit)
                nach_links_korrigieren(korrektur)

                letzte_position = -1

                aktion = f"LINKS KORRIGIEREN | Korrektur={korrektur} "

            # ── Nur rechts -> Linie ist rechts, Notfall rechts ─
            elif rechts == 1 and mitte == 0 and links == 0:
                if aktuelle_kurvenrichtung != 1:
                    kurven_startzeit = jetzt
                    aktuelle_kurvenrichtung = 1

                korrektur = berechne_korrektur(kurven_startzeit, letzte_mitte_zeit)
                nach_rechts_korrigieren(korrektur)

                letzte_position = 1

                aktion = f"RECHTS KORRIGIEREN | Korrektur={korrektur}"

            # ── Links + rechts -> Kreuzung oder Linie zu breit ─
            elif links == 1 and rechts == 1:
                geradeaus_fahren()

                aktuelle_kurvenrichtung = 0
                kurven_startzeit = None
                letzte_mitte_zeit = jetzt

                aktion = "GERADEAUS / KREUZUNG"

            # ── Gar kein Sensor -> Linie weg, suchen ─
            else:
                if letzte_position == -1:
                    # Linie war links -> weiter links suchen
                    if aktuelle_kurvenrichtung != -1:
                        kurven_startzeit = jetzt
                        aktuelle_kurvenrichtung = -1

                    korrektur = berechne_korrektur(kurven_startzeit, letzte_mitte_zeit)
                    nach_links_korrigieren(korrektur)

                    aktion = f"SUCHE LINKS | Korrektur={korrektur} "

                elif letzte_position == 1:
                    # Linie war rechts -> weiter rechts suchen
                    if aktuelle_kurvenrichtung != 1:
                        kurven_startzeit = jetzt
                        aktuelle_kurvenrichtung = 1

                    korrektur = berechne_korrektur(kurven_startzeit, letzte_mitte_zeit)
                    nach_rechts_korrigieren(korrektur)

                    aktion = f"SUCHE RECHTS | Korrektur={korrektur}"

                else:
                    # Linie war mittig und ist weg -> vorsichtig links suchen
                    korrektur = KORREKTUR_GERADE
                    nach_links_korrigieren(korrektur)

                    aktuelle_kurvenrichtung = -1
                    kurven_startzeit = jetzt

                    aktion = f"SUCHE LEICHT LINKS | Korrektur={korrektur}"

            print(f"Links={links} Mitte={mitte} Rechts={rechts} | {aktion}")

            time.sleep(REGEL_PAUSE)

    except KeyboardInterrupt:
        protokoll.info("Abbruch durch Nutzer")

    finally:
        alle_motoren_stoppen()
        protokoll.info("Motoren gestoppt")
