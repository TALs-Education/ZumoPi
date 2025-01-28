#!/usr/bin/env python3

from picamzero import Camera
from PIL import Image

cam = Camera()
frame_array = cam.capture_array()

# Save it to disk, so you can confirm the camera works
Image.fromarray(frame_array).save("test.jpg")
print("Saved 'test.jpg' — open this file to verify that the camera captured an image.")
