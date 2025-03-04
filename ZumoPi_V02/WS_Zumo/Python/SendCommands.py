import serial
import time

# Open serial port
ser = serial.Serial('/dev/ttyAMA10', 115200, timeout=1)
time.sleep(1)  # Allow some time for the connection to initialize
# Move forward (both wheels at 150)
ser.write(b'{"vl":150,"vr":150}\n')
time.sleep(0.5)
# Rotate in place (left wheel forward, right wheel backward)
ser.write(b'{"vl":150,"vr":-150}\n')
time.sleep(0.5)
# Stop
ser.write(b'{"vl":0,"vr":0}\n')
ser.close()