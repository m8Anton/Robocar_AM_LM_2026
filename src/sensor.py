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

    Die Variable SENSOR_AKTIV_BEDEUTET_KEINE_LINIE kann die Logik umdrehen.
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
