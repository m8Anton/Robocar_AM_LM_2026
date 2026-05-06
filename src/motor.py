import board
from adafruit_pca9685 import PCA9685
import time
import logging

log = logging.getLogger(__name__)

i2c = board.I2C()
pca = PCA9685(i2c)


current_speed_front_left = 0
current_speed_front_right = 0
current_speed_back_left = 0
current_speed_back_right = 0

def init():
    log.info("Initializing motor controller_PWM")
    pca.frequency = 50
    pca.channels[0].duty_cycle = 0
    pca.channels[1].duty_cycle = 0
    pca.channels[2].duty_cycle = 0
    pca.channels[3].duty_cycle = 0
    pca.channels[4].duty_cycle = 0
    pca.channels[5].duty_cycle = 0
    pca.channels[6].duty_cycle = 0
    pca.channels[7].duty_cycle = 0
    pass

def stop_all():
    pca.channels[0].duty_cycle = 0
    pca.channels[1].duty_cycle = 0
    pca.channels[2].duty_cycle = 0
    pca.channels[3].duty_cycle = 0
    pca.channels[4].duty_cycle = 0
    pca.channels[5].duty_cycle = 0
    pca.channels[6].duty_cycle = 0
    pca.channels[7].duty_cycle = 0
    current_speed_front_left = 0
    current_speed_front_right = 0
    current_speed_back_left = 0
    current_speed_back_right = 0    

def front_left(speed=0):
    if 0 > abs(speed) > 100:
        log.error(f"Speed {speed} must be between -1000 and 1000")
        return

    motor_speed = int((abs(speed) * 0xFFFF) / 100)
    current_speed_front_left = speed

    if speed >= 0:
        pca.channels[0].duty_cycle = 0
        pca.channels[1].duty_cycle = motor_speed
    if speed < 0:
        pca.channels[0].duty_cycle = motor_speed
        pca.channels[1].duty_cycle = 0
        
def rear_right(speed=0):
    if 0 > abs(speed) > 100:
        log.error(f"Speed {speed} must be between -1000 and 1000")
        return

    motor_speed = int((abs(speed) * 0xFFFF) / 100)
    current_speed_back_right = speed

    if speed >= 0:
        pca.channels[6].duty_cycle = 0
        pca.channels[7].duty_cycle = motor_speed
    if speed < 0:
        pca.channels[6].duty_cycle = motor_speed
        pca.channels[7].duty_cycle = 0