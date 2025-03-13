import sys
import cv2
import numpy as np

def print_usage():
    print("Usage: python extended_webcam_demo.py <mode>")
    print("Available modes:")
    print("  none        - No processing, just display the original feed")
    print("  grayscale   - Convert frames to grayscale")
    print("  hsv_mask    - Color masking in HSV (example: blue range)")
    print("  contour     - Simple contour detection on binary threshold")
    print("  lines       - Detect lines using HoughLinesP")
    print("  circles     - Detect circles using HoughCircles")

if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

mode = sys.argv[1].lower()

# Open default webcam (index 0).
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Could not open webcam.")
    sys.exit(1)

print(f"Running mode: {mode}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame from webcam.")
        break

    # We'll create a "display_frame" to show the processed result.
    display_frame = frame.copy()

    if mode == "none":
        # Simply display the original feed without modifications.
        pass  # display_frame is already frame.copy()

    elif mode == "grayscale":
        # Convert to grayscale.
        display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    elif mode == "hsv_mask":
        # Convert to HSV color space for color masking.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Example: blue color range (tweak as needed).
        lower_blue = (100, 150, 50)
        upper_blue = (140, 255, 255)
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        display_frame = mask  # This shows the mask as a grayscale image.

    elif mode == "contour":
        # Convert to grayscale, then threshold to get a binary image.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Draw the contours in green on the original frame.
        cv2.drawContours(display_frame, contours, -1, (0, 255, 0), 2)

    elif mode == "lines":
        # Detect edges with Canny, then apply probabilistic Hough lines.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    elif mode == "circles":
        # Use a blur to reduce noise, then detect circles using HoughCircles.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2, minDist=50,
                                   param1=100, param2=30,
                                   minRadius=10, maxRadius=150)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for (x, y, r) in circles[0, :]:
                cv2.circle(display_frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(display_frame, (x, y), 2, (0, 0, 255), 3)  # Mark center

    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        break

    # Show the processed result.
    cv2.imshow("Extended Webcam Demo", display_frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()