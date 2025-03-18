import sys
import cv2
import numpy as np
from picamera2 import Picamera2

def print_usage():
    print("Usage: python feature_extraction_demo.py <mode>")
    print("Available modes:")
    print("  lines       - Detect lines using HoughLinesP")
    print("  circles     - Detect circles using HoughCircles")
    print("  contours    - Detect contours using cv2.findContours")
    print("  components  - Detect connected components using cv2.connectedComponentsWithStats")

# Parse command-line argument
if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

mode = sys.argv[1].lower()

# Initialize camera
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration({"format": "RGB888", "size": (640, 480)})
picam2.configure(preview_config)
picam2.start()

print(f"Running feature extraction mode: {mode}")

while True:
    frame = picam2.capture_array()
    display_frame = frame.copy()

    # Convert to grayscale (common prerequisite for many feature extraction methods)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if mode == "lines":
        # Use Canny edge detection before applying HoughLinesP
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=10)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    elif mode == "circles":
        # Use a blur to reduce noise and improve circle detection
        blurred = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
            param1=100, param2=50, minRadius=50, maxRadius=150
        )
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                cv2.circle(display_frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(display_frame, (x, y), 2, (0, 0, 255), 3)  # Mark center

    elif mode == "contours":
        # Simple thresholding to create a binary image for contour detection
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            cv2.drawContours(display_frame, [cnt], 0, (0, 255, 0), 2)

    elif mode == "components":
        # Threshold and then use connectedComponentsWithStats
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        # Start from 1 to skip background (label 0)
        for label in range(1, num_labels):
            x, y, w, h, area = stats[label]
            cx, cy = centroids[label]
            # Draw bounding box and mark centroid
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(display_frame, (int(cx), int(cy)), 3, (0, 0, 255), -1)

    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)

    # Display the result
    cv2.imshow("Feature Extraction Demo", display_frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()