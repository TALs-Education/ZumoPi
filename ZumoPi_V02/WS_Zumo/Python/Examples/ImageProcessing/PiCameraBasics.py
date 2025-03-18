import sys
import time
import cv2
from picamera2 import Picamera2
import numpy as np

def print_usage():
    print("Usage: python image_processing_demo.py <mode> [threshold]")
    print("Available modes:")
    print("  grayscale      - Convert image to grayscale")
    print("  hsv_mask       - Color masking in HSV space (example: blue range)")
    print("  threshold      - Binary thresholding (optional threshold value)")
    print("  morph_open     - Morphological opening (noise removal)")
    print("  none           - No processing (just display original)")
    print("\nOptional:")
    print("  [threshold]    - Integer (0-255) for binary thresholding, default is 127")

# --- Parse command-line arguments ---
if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

mode = sys.argv[1].lower()
threshold = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 127  # Default threshold = 127

# Initialize camera
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration({"format": "RGB888", "size": (640, 480)})
picam2.configure(preview_config)
picam2.start()

print(f"Running mode: {mode} with threshold: {threshold}")

while True:
    frame = picam2.capture_array()

    # --- Grayscale ---
    if mode == "grayscale":
        processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display_frame = processed_frame

    # --- HSV Color Mask (Blue) ---
    elif mode == "hsv_mask":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_blue = (100, 150, 50)   # Lower bound of blue in HSV
        upper_blue = (140, 255, 255)  # Upper bound of blue in HSV
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        display_frame = mask_blue  # Displays the mask as a grayscale image

    # --- Thresholding (Dynamic Value) ---
    elif mode == "threshold":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        display_frame = binary

    # --- Morphological Opening (Noise Removal) ---
    elif mode == "morph_open":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        kernel_size = (3, 3)  # Adjustable kernel size
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
        binary_clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        display_frame = binary_clean

    # --- No Processing ---
    elif mode == "none":
        display_frame = frame

    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        sys.exit(1)

    # Display the result
    cv2.imshow("Image Processing Demo", display_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()