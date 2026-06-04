import RPi.GPIO as GPIO
import time


IR_SENSORS = [21, 20, 16, 12]
GPIO.setmode(GPIO.BCM)
for sensor in IR_SENSORS:
    GPIO.setup(sensor, GPIO.IN)

while(1):
    print("21",GPIO.input(21))
    print("20",GPIO.input(20))
    print("16",GPIO.input(16))
    print("12",GPIO.input(12))
    time.sleep(1)
