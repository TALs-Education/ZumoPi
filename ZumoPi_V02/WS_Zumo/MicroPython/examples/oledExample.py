from machine import Pin, I2C
import ssd1306
import time

# Initialize I2C on pins GP5 (SCL) and GP4 (SDA) at 400kHz
i2c = I2C(id=0, scl=Pin(5), sda=Pin(4), freq=400_000)

# If your SSD1306 uses address 0x3D (instead of 0x3C),
# specify addr=0x3D when creating the display object:
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3D)

# Clear the display
oled.fill(0)

# Print "Hello World"
oled.text("Hello World", 0, 0)

# Update the OLED to show the text
oled.show()

# Keep the program running so the display doesn't clear
while True:
    time.sleep(1)