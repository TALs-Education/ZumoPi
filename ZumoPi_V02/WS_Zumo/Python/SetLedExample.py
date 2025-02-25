#!/usr/bin/env python3
import serial
import time
import threading
import json

def uart_receive(ser):
    """Continuously read from the UART port and print complete messages."""
    buffer = ""
    while True:
        try:
            if ser.in_waiting > 0:
                # Read available bytes and append them to the buffer.
                data = ser.read(ser.in_waiting)
                buffer += data.decode('utf-8', errors='replace')
                # Process any complete messages (terminated with a newline).
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        print("Received:", line)
        except Exception as e:
            print("Error reading from UART:", e)
        time.sleep(0.01)

def uart_send(ser):
    """Prompt the user for LED number and color, then send a JSON command over UART."""
    while True:
        try:
            # Get LED number from the user.
            led_input = input("Enter LED number (or 'exit' to quit): ")
            if led_input.lower() == 'exit':
                break
            try:
                led_number = int(led_input)
            except ValueError:
                print("Invalid LED number. Please enter an integer.")
                continue

            # Get the color from the user.
            color = input("Enter color: ")

            # Build and encode the JSON command.
            command = {"LEDNumber": led_number, "Color": color}
            json_command = json.dumps(command) + "\n"  # Append newline as delimiter.
            ser.write(json_command.encode('utf-8'))
            print("Sent command:", json_command.strip())
        except Exception as e:
            print("Error writing to UART:", e)

def main():
    try:
        ser = serial.Serial(
            port="/dev/ttyAMA10",  # Adjust this port as needed.
            baudrate=115200,
            timeout=0.1  # Short timeout for non-blocking reads.
        )
        print("UART port /dev/ttyAMA10 opened successfully.")
    except serial.SerialException as e:
        print("Error opening UART port:", e)
        return

    # Create and start the receiving and sending threads.
    recv_thread = threading.Thread(target=uart_receive, args=(ser,), daemon=True)
    send_thread = threading.Thread(target=uart_send, args=(ser,), daemon=True)
    
    recv_thread.start()
    send_thread.start()

    # Keep the main thread alive until the user chooses to exit.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    finally:
        ser.close()
        print("Serial port closed.")

if __name__ == '__main__':
    main()
