import time
import math
import cv2
import numpy as np
from picamera2 import Picamera2

# --- Debug Flag ---
DEBUG = False  # Set to True to show the grayscale image with all candidate contours

# --- Camera and Object Parameters ---
CAMERA_HEIGHT = 85.0       # mm above ground
CAMERA_TILT_DEG = 25     # Camera tilted downward theoreticly 25 Deg, adjusted based on measurments.
CAMERA_TILT_RAD = math.radians(CAMERA_TILT_DEG)
HORIZONTAL_FOV_DEG = 102.0 # Horizontal field of view in degrees
VERTICAL_FOV_DEG = 67.0    # Vertical field of view in degrees

DISK_DIAMETER = 27.5       # mm (full black+white disk)
CENTER_WHITE = 7.0         # mm (white center diameter)

# --- Blob Filtering Parameters ---
MIN_BLACK_AREA = 250      # Minimum acceptable area for the black blob
MAX_BLACK_AREA = 7500     # Maximum acceptable area for the black blob
MIN_WHITE_FRACTION = 0.01 # Minimum fraction of white inside the black blob
MAX_WHITE_FRACTION = 0.1  # Maximum fraction of white inside the black blob

# Initialize PiCamera2
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration({"format": "RGB888", "size": (640, 480)})
picam2.configure(preview_config)
picam2.start()

prev_frame_time = time.time()

try:
    while True:
        # Record loop start time to limit FPS to 10
        loop_start = time.time()
        
        frame = picam2.capture_array()  # Captured frame in BGR order
        height, width, _ = frame.shape
        
        # ----------------------------------------------------------
        # 1) Convert to grayscale and blur to reduce noise
        # ----------------------------------------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (3, 3), 2)

        # ----------------------------------------------------------
        # 2) Threshold to isolate dark areas (the black blob).
        #    Invert so that the black blob becomes white in the mask.
        # ----------------------------------------------------------
        thresh_value = 95  # Adjust as needed
        _, black_mask = cv2.threshold(gray_blurred, thresh_value, 255, cv2.THRESH_BINARY_INV)

        # Optionally, apply morphological operations to clean noise:
        # kernel = np.ones((3,3), np.uint8)
        # black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, kernel)

        # Also threshold for white regions (to detect the small white blob inside)
        white_thresh = 200  # Adjust as needed
        _, white_mask = cv2.threshold(gray_blurred, white_thresh, 255, cv2.THRESH_BINARY)

        # ----------------------------------------------------------
        # 3) Find contours in the black_mask
        # ----------------------------------------------------------
        contours, _ = cv2.findContours(black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidate_contours = []  # Store candidates that pass area filtering
        best_center = None
        best_perimeter = None
        best_fraction_white = None
        best_candidate_contour = None
        best_candidate_area = None

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_BLACK_AREA or area > MAX_BLACK_AREA:
                continue

            candidate_contours.append(cnt)

            # Create a filled mask for this candidate
            candidate_mask = np.zeros_like(gray)
            cv2.drawContours(candidate_mask, [cnt], -1, 255, thickness=-1)
            
            # Calculate the white area inside this candidate region
            candidate_white = cv2.bitwise_and(white_mask, candidate_mask)
            white_area = cv2.countNonZero(candidate_white)
            fraction_white = white_area / float(area)

            # Check if the white fraction is within the expected range
            if MIN_WHITE_FRACTION < fraction_white < MAX_WHITE_FRACTION:
                # Compute the center of the blob using moments
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                else:
                    cX, cY = 0, 0

                best_center = (cX, cY)
                best_perimeter = cv2.arcLength(cnt, closed=True)
                best_fraction_white = fraction_white
                best_candidate_contour = cnt
                best_candidate_area = area
                # Stop after the first valid candidate is found; remove break to process further
                break

        # ----------------------------------------------------------
        # 4) Draw overlays for debug and best candidate
        # ----------------------------------------------------------
        # In debug mode, draw all candidate contours (from area filtering) in blue
        if DEBUG:
            for cnt in candidate_contours:
                cv2.drawContours(frame, [cnt], -1, (0, 0, 255), 1)

        # If a candidate blob passed the white fraction test, draw it and compute coordinates
        if best_candidate_contour is not None:
            # Highlight the best candidate contour in green
            cv2.drawContours(frame, [best_candidate_contour], -1, (0, 255, 0), 2)
            # Draw the center in red
            cv2.circle(frame, best_center, 5, (0, 0, 255), -1)

            # Compute real‐world ground coordinates using the pinhole model
            cx_img = width / 2.0
            cy_img = height / 2.0
            u = best_center[0]
            v = best_center[1]

            # Calculate image-centered coordinates (offset from image center)
            uc = u - cx_img
            vc = v - cy_img

            # Convert offsets to angles (in degrees then to radians)
            alpha_deg = (uc / (width / 2.0)) * (HORIZONTAL_FOV_DEG / 2.0)
            beta_deg  = (vc / (height / 2.0)) * (VERTICAL_FOV_DEG / 2.0)
            alpha_rad = math.radians(alpha_deg)
            beta_rad  = math.radians(beta_deg)

            # Total pitch angle (camera tilt + beta)
            gamma_rad = CAMERA_TILT_RAD + beta_rad

            # Ground-plane distance: R = H / tan(gamma)
            if abs(math.tan(gamma_rad)) > 1e-6:
                R = CAMERA_HEIGHT / math.tan(gamma_rad)
            else:
                R = 999999.9

            # Compute X offset from camera centerline
            X_world = R * math.tan(alpha_rad)
            # Factor in y axis and offset from car bumper to adjust to real world measurments
            Y_world = R * math.sqrt(2)+25.0 

            # Overlay computed position, perimeter, white fraction, and pixel coordinates
            pos_text = f"X={X_world:.1f}mm, Y={Y_world:.1f}mm"
            cv2.putText(frame, pos_text, (best_center[0]+10, best_center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            perimeter_text = f"Perim: {best_perimeter:.1f}px"
            cv2.putText(frame, perimeter_text, (best_center[0]+10, best_center[1]+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            fraction_text = f"Fraction: {best_fraction_white:.2f}"
            cv2.putText(frame, fraction_text, (best_center[0]+10, best_center[1]+50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            pixel_text = f"Pixel: (v={v}, u={u})"
            cv2.putText(frame, pixel_text, (best_center[0]+10, best_center[1]+75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            area_text = f"Area: {best_candidate_area:.1f}px"
            cv2.putText(frame, area_text, (best_center[0]+10, best_center[1]+100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ----------------------------------------------------------
        # Overlay FPS and resolution
        # ----------------------------------------------------------
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # ----------------------------------------------------------
        # Show final image: if DEBUG is enabled, show grayscale (with overlays); otherwise, show BGR
        # ----------------------------------------------------------
        if DEBUG:
            cv2.imshow("Live Feed", frame)
        else:
            cv2.imshow("Live Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # ----------------------------------------------------------
        # Limit the loop to 10 FPS (minimum loop duration = 0.1 sec)
        # ----------------------------------------------------------
        elapsed = time.time() - loop_start
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
finally:
    cv2.destroyAllWindows()
    picam2.stop()
