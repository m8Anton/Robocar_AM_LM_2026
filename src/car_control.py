import time
import logging

from motor import fahren, alle_motoren_stoppen
from sensor import liniensensoren_lesen

protokoll = logging.getLogger(__name__)

# ── Einstellungen ───────────────────────────────────────────
GRUND_GESCHWINDIGKEIT = 25
DREH_GESCHWINDIGKEIT = 40
SUCH_GESCHWINDIGKEIT = 40
SUCH_INVENTIERTGESCHWINDIGKEIT = -20


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
    fahren(SUCH_GESCHWINDIGKEIT, SUCH_INVENTIERTGESCHWINDIGKEIT)


def rechte_motoren_suche() -> None:
    """
    Nur die rechte Motorseite fährt langsam beim Suchen der Linie.
    """
    fahren(SUCH_INVENTIERTGESCHWINDIGKEIT, SUCH_GESCHWINDIGKEIT)


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

            # Der mittlere Sensor sieht die Linie.
            # Der Roboter ist richtig ausgerichtet und fährt geradeaus.
            if mitte == 1:
                geradeaus_fahren()
                letzte_position = 0
                aktion = "GERADEAUS"

            # Der linke Sensor sieht die Linie.
            # die rechten Motoren fahren.
            elif links == 1 and rechts == 0:
                rechte_motoren_an()
                letzte_position = -1
                aktion = "RECHTE MOTOREN AN, weil LINKS aktiv"

            # Der rechte Sensor sieht die Linie.
            # die linken Motoren fahren.
            elif rechts == 1 and links == 0:
                linke_motoren_an()
                letzte_position = 1
                aktion = "LINKE MOTOREN AN, weil RECHTS aktiv"

            # Links und rechts sehen gleichzeitig die Linie.
            # Das kann eine breite Linie, eine Kreuzung oder ein Sensorfehler sein.
            # In diesem Fall fährt der Roboter vorsichtig geradeaus.
            elif links == 1 and rechts == 1:
                geradeaus_fahren()
                aktion = "GERADEAUS, breite Linie oder Kreuzung"

            # Kein Sensor sieht die Linie.
            # Der Roboter sucht abhängig wo er die Linie zuletzt gesehen hat.
            else:
                if letzte_position == -1:
                    # Zuletzt war links aktiv.
                    # Also sollen weiterhin die rechten Motoren laufen.
                    rechte_motoren_suche()
                    aktion = "SUCHE: RECHTE MOTOREN, weil zuletzt LINKS aktiv"

                elif letzte_position == 1:
                    # Zuletzt war rechts aktiv.
                    # Also sollen weiterhin die linken Motoren laufen.
                    linke_motoren_suche()
                    aktion = "SUCHE: LINKE MOTOREN, weil zuletzt RECHTS aktiv"

                else:
                    # Zuletzt war der mittlere Sensor aktiv.
                    # Standardmäßig mit rechter Motorseite suchen.
                    rechte_motoren_suche()
                    aktion = "SUCHE STANDARD: RECHTE MOTOREN"

            print(f"Links={links} Mitte={mitte} Rechts={rechts} | {aktion}")

            time.sleep(0.03)

    except KeyboardInterrupt:
        protokoll.info("Abbruch durch Nutzer")

    finally:
        alle_motoren_stoppen()
        protokoll.info("Motoren gestoppt")
