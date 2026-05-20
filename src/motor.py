import board
from adafruit_pca9685 import PCA9685
from gpiozero import LineSensor
import time
import logging

log = logging.getLogger(__name__)

# ── Hardware ────────────────────────────────────────────────
i2c = board.I2C()
pca = PCA9685(i2c)

mitte = LineSensor(15)
links  = LineSensor(14)
rechts = LineSensor(23)

# ── PID Parameter  ──────────────────────────────
BASE_SPEED = 20
Kp = 10.0
Ki = 1.0
Kd = 0.5

MAX_CORRECTION = 10

# ── Hilfsfunktionen ─────────────────────────────────────────
def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))

def speed_to_duty(speed: float) -> int:
    return int((abs(speed) * 0xFFFF) / 100)

def set_motor(ch_fwd: int, ch_rev: int, speed: float) -> None:
    speed = clamp(speed, -100, 100)
    duty  = speed_to_duty(speed)
    if speed >= 0:
        pca.channels[ch_fwd].duty_cycle = 0
        pca.channels[ch_rev].duty_cycle = duty
    else:
        pca.channels[ch_fwd].duty_cycle = duty
        pca.channels[ch_rev].duty_cycle = 0

def init() -> None:
    log.info("PWM initialisieren")
    pca.frequency = 50
    for ch in range(8):
        pca.channels[ch].duty_cycle = 0

def stop_all() -> None:
    for ch in range(8):
        pca.channels[ch].duty_cycle = 0

def drive(left_speed: float, right_speed: float) -> None:
    set_motor(0, 1,  left_speed)
    set_motor(6, 7, -left_speed)
    set_motor(2, 3, -right_speed)
    set_motor(4, 5,  right_speed)

# ── PID Regler ───────────────────────────────────────────────
def pid_line_follow(duration: float = 20) -> None:
    integral   = 0.0
    last_error = 0.0
    last_time  = time.monotonic()
    start_time = last_time

    log.info("PID Linienfolge gestartet")

    try:
        while (time.monotonic() - start_time) < duration:
            now = time.monotonic()
            dt  = now - last_time
            if dt == 0:
                dt = 0.001
            last_time = now

            # ── Sensorwerte (type-safe) ──────────────────
            l = int(bool(links.is_active))
            m = int(bool(mitte.is_active))
            r = int(bool(rechts.is_active))

            # ── Fehlerberechnung ─────────────────────────
            error = float(r - l)

            # Linie verloren → letzten Fehler beibehalten
            if r == 0 and m == 0 and l == 0:
                error = last_error

            # ── PID Terme ────────────────────────────────
            integral   += error * dt
            derivative  = (error - last_error) / dt
            last_error  = error

            correction = Kp * error + Ki * integral + Kd * derivative
            correction  = clamp(correction, -MAX_CORRECTION, MAX_CORRECTION)

            # ── Motorsteuerung ───────────────────────────
            left_speed  = clamp(BASE_SPEED - correction, 0, 100)
            right_speed = clamp(BASE_SPEED + correction, 0, 100)

            drive(left_speed, right_speed)

            print(f"L={l} M={m} R={r} | ")

            time.sleep(0.02)

    except KeyboardInterrupt:
        log.info("Abbruch durch Nutzer")
    finally:
        stop_all()
        log.info("Motoren gestoppt")

# ── Main ─────────────────────────────────────────────────────
def main() -> None:
    init()
    pid_line_follow(duration=60)

if __name__ == "__main__":
    main()
