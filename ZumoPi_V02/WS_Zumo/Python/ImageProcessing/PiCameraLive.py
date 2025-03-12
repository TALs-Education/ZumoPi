import cv2
from picamera2 import Picamera2
import time

# Initialize the Camera
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(
    {"format": "RGB888", "size": (640, 480)}
)
picam2.configure(preview_config)
picam2.start()

# Capture, Display, and Save an Image
while True:
    frame = picam2.capture_array()  # Capture frame from camera
    
    cv2.imshow("Live Feed", frame)  # Display live feed
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        filename = f"captured_{int(time.time())}.jpg"  # Unique filename with timestamp
        cv2.imwrite(filename, frame)  # Save the image
        print(f"Image saved as {filename}")
    elif key == ord('q'):
        break  # Quit the program

cv2.destroyAllWindows()