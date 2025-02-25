import machine
import utime

# Configure UART0 on the Pico using pins 28 (RX) and 29 (TX)
uart = machine.UART(0, baudrate=115200, tx=machine.Pin(28), rx=machine.Pin(29))

# Send a message
uart.write("Hello from Pico UART1!\n")

# Wait to receive data and print it out
while True:
    if uart.any():
        data = uart.readline()
        if data:
            print("Received:", data)
            uart.write("Received:")
            uart.write(data)
    utime.sleep(0.1)
