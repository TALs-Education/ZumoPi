import cv2
import numpy as np
import matplotlib.pyplot as plt
from hub_detector import detect_hubs  # Import the function from your library

# --- Example usage ---
if __name__ == '__main__':
    # Load an image using OpenCV (convert BGR to RGB)
    img_bgr = cv2.imread('Image11.jpg')
    if img_bgr is None:
        raise IOError("Image not found!")
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    # Call the new function with DEBUG=True to see intermediate outputs.
    hubs = detect_hubs(img_rgb, DEBUG=True, circle_diameter=200,
                       expected_dark_fraction=0.85, min_blob_area=200*5) # blob size diameter*resolution/200 1080p = 5
    print("Detected hubs:", hubs)

