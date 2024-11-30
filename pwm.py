import time
import RPi.GPIO as GPIO

# Pin definitions
led_pin = 12

# Use "GPIO" pin numbering
GPIO.setmode(GPIO.BCM)

# Set LED pin as output
GPIO.setup(led_pin, GPIO.OUT)

# Initialize pwm object with 50 Hz and 0% duty cycle
pwm = GPIO.PWM(led_pin, 200)
pwm.stop()
pwm.ChangeDutyCycle(50)
pwm.start(50)
time.sleep(2000)
# Set PWM duty cycle to 50%, wait, then to 90%
#pwm.ChangeDutyCycle(50)
#time.sleep(2)
#pwm.ChangeDutyCycle(90)
#time.sleep(2)

# Stop, cleanup, and exit
pwm.stop()
GPIO.cleanup()
