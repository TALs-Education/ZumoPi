from picamera2 import Picamera2
import cv2
import time
import numpy as np
import math

# --- Camera and Object Parameters ---
CAMERA_HEIGHT = 85.0       # mm above the ground
CAMERA_TILT_DEG = 25.0     # Camera tilted downward by 25 degrees
CAMERA_TILT_RAD = math.radians(CAMERA_TILT_DEG)
HORIZONTAL_FOV_DEG = 102.0 # Horizontal field of view (degrees)
VERTICAL_FOV_DEG = 67.0    # Vertical field of view (degrees)

BALL_DIAMETER = 60.0       # mm (real-world diameter)
BALL_RADIUS_REAL = BALL_DIAMETER / 2.0  # 30 mm

# --- Camera Initialization ---
picam2 = Picamera2()
# Use "RGB888" so that frames are in BGR order for OpenCV.
preview_config = picam2.create_preview_configuration({"format": "RGB888", "size": (640, 480)})
# Uncomment the following line to change the resolution (e.g., to 1280x720)
# preview_config["main"]["size"] = (1280, 720)
picam2.configure(preview_config)
picam2.start()

prev_frame_time = time.time()

# --- Corrected Projection Function ---
def project_y(Y_world, Z_world, f_y, cy):
    """
    Projects a world point (with vertical coordinate Y_world and ground distance Z_world)
    to an image vertical coordinate.
    """
    Y_rel = CAMERA_HEIGHT - Y_world  # positive if point is below the camera
    Y_cam = math.cos(CAMERA_TILT_RAD) * Y_rel - math.sin(CAMERA_TILT_RAD) * Z_world
    Z_cam = math.sin(CAMERA_TILT_RAD) * Y_rel + math.cos(CAMERA_TILT_RAD) * Z_world
    return f_y * (Y_cam / Z_cam) + cy

# Function to draw multiple lines of text centered at a given point.
def draw_centered_text(img, lines, center_x, center_y, font=cv2.FONT_HERSHEY_SIMPLEX, 
                       font_scale=0.5, thickness=2, line_spacing=5, color=(0,255,255)):
    # Compute height for one line (all lines use the same font & scale).
    (text_width, text_height), baseline = cv2.getTextSize(lines[0], font, font_scale, thickness)
    total_height = (text_height + line_spacing) * len(lines) - line_spacing
    # Starting y: center the block vertically around center_y.
    y0 = int(center_y - total_height / 2 + text_height)
    for i, line in enumerate(lines):
        (w, h), _ = cv2.getTextSize(line, font, font_scale, thickness)
        x = int(center_x - w / 2)
        y = y0 + i * (h + line_spacing)
        cv2.putText(img, line, (x, y), font, font_scale, color, thickness)

try:
    while True:
        # Capture frame (BGR order).
        frame = picam2.capture_array()
        height, width, _ = frame.shape

        # Intrinsic parameters.
        cx = width / 2.0
        cy_img = height / 2.0  # image center y
        f_x = (width / 2.0) / math.tan(math.radians(HORIZONTAL_FOV_DEG / 2.0))
        f_y = (height / 2.0) / math.tan(math.radians(VERTICAL_FOV_DEG / 2.0))
        f_avg = (f_x + f_y) / 2.0

        # Preprocess for circle detection.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Detect circles (minRadius=50 implies minimum visible diameter 100px).
        circles = cv2.HoughCircles(gray_blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2, minDist=100,
                                   param1=100, param2=30,
                                   minRadius=50, maxRadius=0)
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Process only the first detected circle.
            for i in circles[0, :]:
                ball_u, ball_v, radius_pixels = i[0], i[1], i[2]
                # Draw the detected circle and its center.
                cv2.circle(frame, (ball_u, ball_v), 3, (0, 255, 0), -1)
                cv2.circle(frame, (ball_u, ball_v), radius_pixels, (0, 255, 0), 2)
                
                # ----- Initial Distance Estimate -----
                measured_d_pixels = 2 * radius_pixels
                D_est = (f_avg * BALL_DIAMETER) / measured_d_pixels  # in mm
                
                # ----- Compute Projected Y Coordinates Using Corrected Projection -----
                y_center_est = project_y(BALL_RADIUS_REAL, D_est, f_y, cy_img)
                y_contact_est = project_y(0, D_est, f_y, cy_img)
                delta = y_contact_est - y_center_est  # vertical offset (pixels) between contact & ball center
                
                # ----- Correct the Apparent Diameter (spherical model) -----
                r_full = math.sqrt((measured_d_pixels / 2.0)**2 + delta**2)
                d_full = 2 * r_full  # full apparent diameter if unoccluded
                # Corrected distance (include factor of 2).
                D_corr = 2 * (f_avg * BALL_DIAMETER) / d_full

                # ----- Recompute the Ball Center Projection Using Corrected Distance -----
                y_center_corr = project_y(BALL_RADIUS_REAL, D_corr, f_y, cy_img)
                alpha = math.atan((ball_u - cx) / f_x)
                beta = math.atan((y_center_corr - cy_img) / f_y)
                effective_angle = CAMERA_TILT_RAD + beta
                
                ground_distance = D_corr * math.cos(effective_angle)
                X = ground_distance * math.sin(alpha)  # lateral offset (mm)
                Z = ground_distance * math.cos(alpha)  # forward offset (mm)
                vertical_est = D_corr * math.sin(effective_angle)  # vertical drop (mm)
                
                # Compute average color inside the detected circle.
                mask = np.zeros_like(gray)
                cv2.circle(mask, (ball_u, ball_v), radius_pixels, 255, -1)
                mean_val = cv2.mean(frame, mask=mask)  # (B, G, R, A)
                color_text = f"Color: B:{int(mean_val[0])} G:{int(mean_val[1])} R:{int(mean_val[2])}"
                
                # Prepare text lines.
                lines = [
                    f"Diam (pix): {measured_d_pixels}px",
                    f"Img Center: ({ball_u}, {ball_v})",
                    f"Pos: X={X:.1f}mm, Z={Z:.1f}mm",
                    f"Vert: {vertical_est:.1f}mm (exp ~{CAMERA_HEIGHT - BALL_RADIUS_REAL}mm)",
                    f"D: {D_corr:.1f}mm",
                    color_text
                ]
                
                # Draw the text block centered on the ball's center.
                draw_centered_text(frame, lines, ball_u, ball_v, font_scale=0.5, thickness=2, line_spacing=5)
                break  # Process only one ball.
        
        # Compute and overlay FPS and resolution at the bottom left.
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time
        
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.imshow("Live Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cv2.destroyAllWindows()
    picam2.stop()
