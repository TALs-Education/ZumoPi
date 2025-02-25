from picamera2 import Picamera2
import cv2
import time

# Initialize Picamera2
picam2 = Picamera2()

# Create a preview configuration with the desired pixel format and size.
# Using "RGB888" outputs pixels in [B, G, R] order so OpenCV will display them correctly.
preview_config = picam2.create_preview_configuration({"format": "RGB888", "size": (640, 480)})

# Uncomment the following line to change the resolution (e.g., to 1280x720)
# preview_config["main"]["size"] = (1280, 720)

picam2.configure(preview_config)
picam2.start()

# Variables to compute FPS
prev_frame_time = time.time()

try:
    while True:
        # Capture a frame; it will be in BGR order already.
        frame = picam2.capture_array()

        # Compute FPS
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time

        # Retrieve frame resolution
        height, width, _ = frame.shape

        # Overlay text with resolution and FPS
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Display the frame in a window
        cv2.imshow("Live Feed", frame)

        # Exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cv2.destroyAllWindows()
    picam2.stop()
