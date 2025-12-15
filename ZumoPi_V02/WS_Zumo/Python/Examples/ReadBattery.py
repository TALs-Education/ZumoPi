#!/usr/bin/env python3
# Suitable for UPS Shield X1200, X1201, X1202

import struct
import time
import subprocess

import smbus
import gpiod

# ---- Fuel gauge (I2C) ----
I2C_BUS_NUM = 1
ADDRESS = 0x36
VOLTAGE_REG = 0x02
CAPACITY_REG = 0x04

LOW_VOLTAGE = 3.20
LOW_CAPACITY = 20

# Retry behavior for I2C
I2C_RETRIES = 5
I2C_RETRY_DELAY_S = 0.05

# ---- GPIO (Power indication) ----
PLD_PIN = 6
GPIO_CHIP = "gpiochip0"  # kernel >= 6.6.45 (per your note)

def _swap_word(word: int) -> int:
    return struct.unpack("<H", struct.pack(">H", word))[0]

def open_bus() -> smbus.SMBus:
    return smbus.SMBus(I2C_BUS_NUM)

def read_word_retry(bus: smbus.SMBus, reg: int) -> int:
    """
    Robust I2C read with retries. Raises OSError if all retries fail.
    """
    last_err = None
    for _ in range(I2C_RETRIES):
        try:
            return bus.read_word_data(ADDRESS, reg)
        except OSError as e:
            last_err = e
            time.sleep(I2C_RETRY_DELAY_S)
    raise last_err

def read_voltage(bus: smbus.SMBus) -> float:
    raw = read_word_retry(bus, VOLTAGE_REG)
    swapped = _swap_word(raw)
    return swapped * 1.25 / 1000 / 16

def read_capacity(bus: smbus.SMBus) -> int:
    raw = read_word_retry(bus, CAPACITY_REG)
    swapped = _swap_word(raw)
    return int(swapped / 256)

def shutdown_now():
    subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

def get_power_ok(pld_line) -> bool:
    return (pld_line.get_value() == 1)

def charging_status_text(on_external_power: bool, capacity: int | None) -> str:
    if on_external_power:
        if capacity is None:
            return "External Power: ON"
        if capacity >= 100:
            return "External Power: ON"
        return "External Power: ON"
    return "External Power: OFF"

def main():
    # Setup GPIO
    chip = gpiod.Chip(GPIO_CHIP)
    pld_line = chip.get_line(PLD_PIN)
    pld_line.request(consumer="PLD", type=gpiod.LINE_REQ_DIR_IN)

    # Setup I2C
    bus = open_bus()

    shutdown_triggered = False

    try:
        while True:
            on_ext_power = get_power_ok(pld_line)

            voltage = None
            capacity = None

            try:
                voltage = read_voltage(bus)
                capacity = read_capacity(bus)
            except OSError as e:
                # Attempt recovery: close + reopen I2C bus
                try:
                    bus.close()
                except Exception:
                    pass
                time.sleep(0.1)
                bus = open_bus()
                print(f"I2C read error (Errno {getattr(e, 'errno', '?')}): {e}. Reopened I2C bus; will retry next cycle.")

            print("******************")
            print(charging_status_text(on_ext_power, capacity))

            if voltage is not None:
                print(f"Voltage: {voltage:5.2f}V")
            else:
                print("Voltage:  (read failed)")

            if capacity is not None:
                print(f"Battery: {capacity:5d}%")
            else:
                print("Battery:  (read failed)")

            if capacity is not None and capacity < LOW_CAPACITY:
                print("Battery Low")

            # Low-voltage shutdown (only when discharging)
            if (not on_ext_power) and (not shutdown_triggered) and (voltage is not None) and (voltage < LOW_VOLTAGE):
                shutdown_triggered = True
                print("Battery LOW!!!")
                print("Shutdown in 5 seconds (Ctrl+C to cancel)")
                for remaining in range(5, 0, -1):
                    print(f"  {remaining}...")
                    time.sleep(1)
                shutdown_now()
                break

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nCtrl+C received. Exiting cleanly...")

    finally:
        try:
            pld_line.release()
        except Exception:
            pass
        try:
            bus.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
