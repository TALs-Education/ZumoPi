#!/usr/bin/env python3
import serial
import time
import threading

def uart_receive(ser):
    """Continuously read from the UART port and print complete messages."""
    buffer = ""
    while True:
        try:
            # Read all available bytes
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data.decode('utf-8', errors='replace')
                # Process complete messages (lines ending with newline)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        print("Received:", line)
        except Exception as e:
            print("Error reading from UART:", e)
        time.sleep(0.01)

def uart_send(ser):
    """Continuously wait for user input from the console and send it over UART."""
    while True:
        try:
            # Blocking call to wait for user input.
            message = input("Enter message to send: ")
            if message:
                # Append newline to indicate end-of-message.
                ser.write((message + "\n").encode('utf-8'))
        except Exception as e:
            print("Error writing to UART:", e)

def main():
    try:
        ser = serial.Serial(
            port="/dev/ttyAMA10",
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1  # Short timeout for non-blocking reads.
        )
        print("UART port /dev/ttyAMA10 opened successfully.")
    except serial.SerialException as e:
        print("Error opening UART port:", e)
        return

    # Create and start the receive and send threads.
    recv_thread = threading.Thread(target=uart_receive, args=(ser,), daemon=True)
    send_thread = threading.Thread(target=uart_send, args=(ser,), daemon=True)
    
    recv_thread.start()
    send_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    main()
