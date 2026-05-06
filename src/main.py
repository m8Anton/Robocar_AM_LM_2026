from gpiozero import LineSensor
from signal import pause
from time import sleep

def print_when_detectet():
    print("Line detected!")

def print_when_no_detectet():
    print("No line detected.")


mitte = LineSensor(15)
links = LineSensor(14)
rechts = LineSensor(23)


while True:
    print("mitte: " + str(mitte.value))
    print("links: " + str(links.value))
    print("rechts: " + str(rechts.value))
    sleep(0.02)

pause()