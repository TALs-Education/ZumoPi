# Demonstrates smooth color cycling on the RGB LEDs.

from zumo_2040_robot import robot

rgb_leds = robot.RGBLEDs(10)
rgb_leds.set_brightness(5)

rgb_leds.set(6, [255, 0, 0])
rgb_leds.set(7, [255, 0, 0])
rgb_leds.set(8, [255, 0, 0])
rgb_leds.set(9, [255, 0, 0])
rgb_leds.show()
