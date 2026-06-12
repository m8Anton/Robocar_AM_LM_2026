import time
import logging

from motor import fahren, alle_motoren_stoppen
from sensor import liniensensoren_lesen

protokoll = logging.getLogger(__name__)


# ── Grundeinstellungen ──────────────────────────────────────

GRUND_GESCHWINDIGKEIT = 22      # nicht zu schnell, nicht zu langsam, perfekt (laut mir)
MIN_MOTOR = -30                  # ja, rückwärts geht auch. nein, das wollen wir nicht
MAX_MOTOR = 35                   # mehr hab ich probiert, hat niemand gefallen
LOSFAHR_GESCHWINDIGKEIT = 20    # existiert, wird aber gerade ignoriert. bald™

# ── Korrekturwerte ──────────────────────────────────────────

KORREKTUR_GERADE = 5             # kleine Korrektur, kaum merkbar, wie meine Noten
KORREKTUR_START = 8              # damit er nicht gleich am Anfang ausbricht
KORREKTUR_MAX = 40               # ab hier dreht er sich fast auf der Stelle
KORREKTUR_ANSTIEG_PRO_SEKUNDE = 10  # je länger er falsch fährt, desto mehr Panik
GERADE_TOLERANZ = 0.12          # kurz nach Mitte noch sanft korrigieren (Gnadenfrist)
REGEL_PAUSE = 0.03               # kurze Pause, damit der Pi nicht abraucht
KORREKTUR_FAST_MITTE = 5        # fast mittig = fast richtig = fast gut genug

# ── Hilfsfunktionen ─────────────────────────────────────────

def begrenzen(wert: int, minimum: int, maximum: int) -> int:
    # Damit kein Motor mehr bekommt als er verkraften kann
    return max(minimum, min(maximum, wert))


def motoren_setzen(linker_motor: int, rechter_motor: int) -> None:
    # Beide Motoren begrenzen und ansteuern
    # (ja, die Begrenzung ist nötig, hab ich auf die harte Tour gelernt)
    linker_motor = begrenzen(linker_motor, MIN_MOTOR, MAX_MOTOR)
    rechter_motor = begrenzen(rechter_motor, MIN_MOTOR, MAX_MOTOR)
    fahren(linker_motor, rechter_motor)


def geradeaus_fahren() -> None:
    # Beide gleich schnell -> geradeaus. Rocket science.
    motoren_setzen(GRUND_GESCHWINDIGKEIT, GRUND_GESCHWINDIGKEIT)


def berechne_korrektur(
    kurven_startzeit: float | None,
    letzte_mitte_zeit: float
) -> int:
    """
    Berechnet wie stark gegengesteuert wird.
    Direkt nach der Mitte erstmal ruhig bleiben,
    damit er nicht wie ein Besoffener durch Geraden schlingert.
    Je länger er in der Kurve steckt, desto mehr Panik — macht Sinn.
    """
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
    linker_motor = GRUND_GESCHWINDIGKEIT - korrektur * 2
    rechter_motor = GRUND_GESCHWINDIGKEIT + korrektur
    motoren_setzen(linker_motor, rechter_motor)


def nach_rechts_korrigieren(korrektur: int) -> None:
    # Rechts abbremsen, links Gas geben -> dreht nach rechts
    linker_motor = GRUND_GESCHWINDIGKEIT + korrektur
    rechter_motor = GRUND_GESCHWINDIGKEIT - korrektur * 2
    motoren_setzen(linker_motor, rechter_motor)


# ── Linienfolger ────────────────────────────────────────────

def linie_folgen(dauer: float = 60) -> None:
    """
    Der eigentliche Linienfolger. Hier passiert die Magie.
    (Oder das Chaos. Kommt auf den Tag an.)

    Sensorlogik — für alle die's vergessen:
    Nur Mitte aktiv          -> geradeaus, alles gut
    Mitte + links aktiv      -> leicht links korrigieren
    Mitte + rechts aktiv     -> leicht rechts korrigieren
    Nur links aktiv          -> stärker links korrigieren
    Nur rechts aktiv         -> stärker rechts korrigieren
    Kein Sensor aktiv        -> raten und hoffen
    Links + rechts aktiv     -> Kreuzung oder fette Linie -> geradeaus
    """

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

                aktion = f"LEICHT LINKS | Korrektur={korrektur}"

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

                aktion = f"LINKS KORRIGIEREN | Korrektur={korrektur}"

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

            # ── Gar kein Sensor -> Linie weg, suchen und beten ─
            else:
                if letzte_position == -1:
                    # Linie war links -> weiter links suchen
                    if aktuelle_kurvenrichtung != -1:
                        kurven_startzeit = jetzt
                        aktuelle_kurvenrichtung = -1

                    korrektur = berechne_korrektur(kurven_startzeit, letzte_mitte_zeit)
                    nach_links_korrigieren(korrektur)

                    aktion = f"SUCHE LINKS | Korrektur={korrektur}"

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
                    # (irgendwo muss man ja anfangen)
                    korrektur = KORREKTUR_GERADE
                    nach_links_korrigieren(korrektur)

                    aktuelle_kurvenrichtung = -1
                    kurven_startzeit = jetzt

                    aktion = f"SUCHE LEICHT LINKS | Korrektur={korrektur}"

            print(f"Links={links} Mitte={mitte} Rechts={rechts} | {aktion}")

            time.sleep(REGEL_PAUSE)

    except KeyboardInterrupt:
        protokoll.info("Abbruch durch Nutzer")  # aka Lukas hat den Stecker gezogen

    finally:
        alle_motoren_stoppen()
        protokoll.info("Motoren gestoppt")  # ob er vorher gegen was gefahren ist, wissen wir nicht
