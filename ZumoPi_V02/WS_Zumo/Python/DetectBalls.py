from picamera2 import Picamera2
import cv2
import time
import numpy as np

# Initialize Picamera2
picam2 = Picamera2()

# Create a preview configuration with the desired pixel format and size.
# "RGB888" outputs pixels in [B, G, R] order so OpenCV will display them correctly.
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
        
        # Convert frame to grayscale for circle detection.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply a Gaussian blur to reduce noise and improve circle detection.
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        # Use HoughCircles to detect circles.
        # minRadius=50 ensures a minimum diameter of 100 pixels.
        circles = cv2.HoughCircles(gray_blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2,
                                   minDist=100,
                                   param1=100,
                                   param2=30,
                                   minRadius=50,
                                   maxRadius=0)
        
        # If a circle (ball) is detected, draw it and compute its average color.
        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Process only the first detected circle for simplicity.
            for i in circles[0, :]:
                center = (i[0], i[1])
                radius = i[2]
                
                # Draw the center of the circle
                cv2.circle(frame, center, 3, (0, 255, 0), -1)
                # Draw the circle outline
                cv2.circle(frame, center, radius, (0, 255, 0), 2)
                
                # Create a mask for the circle.
                mask = np.zeros_like(gray)
                cv2.circle(mask, center, radius, 255, -1)
                
                # Compute the average color inside the circle.
                mean_val = cv2.mean(frame, mask=mask)  # returns (B, G, R, A)
                color_text = f"Color: B:{int(mean_val[0])} G:{int(mean_val[1])} R:{int(mean_val[2])}"
                
                # Calculate diameter and prepare text with diameter and center coordinates.
                diameter = radius * 2
                info_text = f"Diam: {diameter}px, Center: ({center[0]}, {center[1]})"
                
                # Place the info text near the ball outline.
                # First line: ball diameter and center position.
                cv2.putText(frame, info_text, (center[0] - radius, center[1] - radius - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                # Second line: average color.
                cv2.putText(frame, color_text, (center[0] - radius, center[1] - radius - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                break  # Process only one ball; remove if you want to handle multiple.
        
        # Calculate FPS for overlay.
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time
        
        # Get the frame resolution.
        height, width, _ = frame.shape
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Display the frame.
        cv2.imshow("Live Feed", frame)
        
        # Exit if 'q' is pressed.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cv2.destroyAllWindows()
    picam2.stop()
