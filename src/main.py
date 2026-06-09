import logging
from motor import initialisieren
from car_control import linie_folgen

logging.basicConfig(level=logging.INFO)

def hauptprogramm() -> None:
    """
    Startet das Roboterprogramm. :)
    Ein weiser Mann meinte mal du sollst Code schreiben den nur du verstehst.
    Denn wenn Ihn andere Verstehen dann bsit du ersetzbar. 
    Schütze dich und schreib Code den nur du verstehst:)
    """
    initialisieren()
    linie_folgen(dauer=60)


if __name__ == "__main__":
    hauptprogramm()
