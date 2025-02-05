import machine
import utime
import sys
import select

# Configure UART0 on the Pico using pins 28 (RX) and 29 (TX)
uart = machine.UART(0, baudrate=115200, tx=machine.Pin(28), rx=machine.Pin(29))

def poll_uart():
    """
    Poll the UART for any incoming data.
    If data is available, read the line and echo it back over UART.
    """
    if uart.any():
        data = uart.readline()
        if data:
            print("UART Received:", data)
            uart.write("UART: ")
            uart.write(data)

def poll_console():
    """
    Poll the console (USB/REPL) for input.
    If data is available, strip newline characters, print the message,
    and send it over UART.
    """
    # Use select.select for a non-blocking check on sys.stdin
    rlist, _, _ = select.select([sys.stdin], [], [], 0)
    if sys.stdin in rlist:
        console_line = sys.stdin.readline().strip()  # Removes \r and \n
        if console_line:  # Only process non-empty input
            print("Console Received:", console_line)
            uart.write("Console: " + console_line + "\n")

# Send an initial message over UART
uart.write("Hello from Pico UART0!\n")

while True:
    poll_uart()     # Check for UART data
    poll_console()  # Check for console input
    utime.sleep(0.1)  # Short delay to avoid hogging the CPU
