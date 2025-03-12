import cv2
from picamera2 import Picamera2
import time

# Initialize the camera
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(
    {"format": "RGB888", "size": (640, 480)}
)
picam2.configure(preview_config)
picam2.start()

start_time = time.time()
frame_count = 0

while True:
    frame = picam2.capture_array()
    frame_count += 1
    elapsed_time = time.time() - start_time

    # Print FPS once every second
    if elapsed_time >= 1.0:
        fps = frame_count / elapsed_time
        print(f"FPS: {fps:.2f}")
        frame_count = 0
        start_time = time.time()

    cv2.imshow("Live Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()