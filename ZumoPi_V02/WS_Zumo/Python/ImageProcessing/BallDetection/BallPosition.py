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

try:
    while True:
        frame = picam2.capture_array()  # Captured frame in BGR order.
        height, width, _ = frame.shape

        # Compute intrinsic parameters from known FOV and image size.
        cx = width / 2.0
        cy = height / 2.0
        f_x = (width / 2.0) / math.tan(math.radians(HORIZONTAL_FOV_DEG / 2.0))
        f_y = (height / 2.0) / math.tan(math.radians(VERTICAL_FOV_DEG / 2.0))
        f_avg = (f_x + f_y) / 2.0

        # Convert frame to grayscale and apply a Gaussian blur.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Detect circles using HoughCircles.
        # minRadius=50 enforces a minimum diameter of 100 pixels.
        circles = cv2.HoughCircles(gray_blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2, minDist=100,
                                   param1=100, param2=30,
                                   minRadius=50, maxRadius=0)

        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Process only the first detected circle.
            for i in circles[0, :]:
                ball_u, ball_v, radius_pixels = i[0], i[1], i[2]
                cv2.circle(frame, (ball_u, ball_v), 3, (0, 255, 0), -1)
                cv2.circle(frame, (ball_u, ball_v), radius_pixels, (0, 255, 0), 2)

                measured_d_pixels = 2 * radius_pixels

                # Basic distance calculation (no spherical correction):
                D = (f_avg * BALL_DIAMETER) / measured_d_pixels # in mm

                # Compute horizontal and vertical angular offsets.
                alpha = math.atan((ball_u - cx) / f_x)
                beta = math.atan((ball_v - cy) / f_y)
                # The effective angle takes the camera tilt into account.
                effective_angle = CAMERA_TILT_RAD + beta

                # Compute ground-plane distances.
                ground_distance = D * math.cos(effective_angle)
                X = ground_distance * math.sin(alpha)  # lateral offset (mm)
                Z = ground_distance * math.cos(alpha)  # forward distance (mm)
                vertical_est = D * math.sin(effective_angle)  # vertical drop (mm)

                # Compute average color inside the detected circle.
                mask = np.zeros_like(gray)
                cv2.circle(mask, (ball_u, ball_v), radius_pixels, 255, -1)
                mean_val = cv2.mean(frame, mask=mask)  # (B, G, R, A)
                color_text = f"Color: B:{int(mean_val[0])} G:{int(mean_val[1])} R:{int(mean_val[2])}"

                # Prepare overlay text near the ball.
                diameter_text = f"Diam: {measured_d_pixels}px"
                center_text = f"Center: ({ball_u}, {ball_v})"
                pos_text = f"Pos: X={X:.1f}mm, Z={Z:.1f}mm"
                vert_text = f"Vert: {vertical_est:.1f}mm (exp ~{CAMERA_HEIGHT - BALL_RADIUS_REAL}mm)"
                text_x = ball_u - radius_pixels
                text_y = ball_v - radius_pixels - 10
                cv2.putText(frame, diameter_text, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.putText(frame, center_text, (text_x, text_y - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.putText(frame, pos_text, (text_x, text_y - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.putText(frame, vert_text, (text_x, text_y - 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.putText(frame, color_text, (text_x, text_y - 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                break  # Process only one ball for simplicity.

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
