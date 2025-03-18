#!/usr/bin/python3
import math
import cv2
import base64
import time
import numpy as np

# Global parameters for camera and ball measurements.
CAMERA_HEIGHT = 85.0       # mm above the ground
CAMERA_TILT_DEG = 25.0     # Camera tilted downward by 25 degrees
CAMERA_TILT_RAD = math.radians(CAMERA_TILT_DEG)
HORIZONTAL_FOV_DEG = 102.0 # Horizontal field of view (degrees)
VERTICAL_FOV_DEG = 67.0    # Vertical field of view (degrees)
BALL_DIAMETER = 70.0       # mm (real-world diameter)
BALL_RADIUS_REAL = BALL_DIAMETER / 2.0  # 35 mm

class BallDetect:
    def __init__(self, camera):
        """
        Initialize with a camera object that provides a capture_array() method.
        """
        self.camera = camera
        self.prev_frame_time = time.time()

    @staticmethod
    def project_y(Y_world, Z_world, f_y, cy):
        """
        Projects a world point to an image vertical coordinate.
        """
        Y_rel = CAMERA_HEIGHT - Y_world  # positive if point is below the camera
        Y_cam = math.cos(CAMERA_TILT_RAD) * Y_rel - math.sin(CAMERA_TILT_RAD) * Z_world
        Z_cam = math.sin(CAMERA_TILT_RAD) * Y_rel + math.cos(CAMERA_TILT_RAD) * Z_world
        return f_y * (Y_cam / Z_cam) + cy

    @staticmethod
    def draw_centered_text(img, lines, center_x, center_y, font=cv2.FONT_HERSHEY_SIMPLEX, 
                           font_scale=0.5, thickness=2, line_spacing=5, color=(0, 255, 255)):
        """
        Draws multiple lines of text centered at (center_x, center_y) on the image.
        """
        (text_width, text_height), baseline = cv2.getTextSize(lines[0], font, font_scale, thickness)
        total_height = (text_height + line_spacing) * len(lines) - line_spacing
        y0 = int(center_y - total_height / 2 + text_height)
        for i, line in enumerate(lines):
            (w, h), _ = cv2.getTextSize(line, font, font_scale, thickness)
            x = int(center_x - w / 2)
            y = y0 + i * (h + line_spacing)
            cv2.putText(img, line, (x, y), font, font_scale, color, thickness)

    def process_frame(self):
        """
        Captures a frame from the camera (expected at 640x480), processes it by detecting balls,
        then selects the candidate whose measured diameter (in pixels) is closest to the expected
        diameter computed from its distance. Diagnostic data is overlaid, FPS is computed, and the
        frame is downscaled to 480x360 before being JPEG-encoded (quality 50) and returned as a
        Base64 string.
        """
        frame = self.camera.capture_array()
        height, width, _ = frame.shape

        # Calculate intrinsic parameters.
        cx = width / 2.0
        cy_img = height / 2.0
        f_x = (width / 2.0) / math.tan(math.radians(HORIZONTAL_FOV_DEG / 2.0))
        f_y = (height / 2.0) / math.tan(math.radians(VERTICAL_FOV_DEG / 2.0))
        f_avg = (f_x + f_y) / 2.0

        # Preprocess the image for circle detection.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # Use stricter parameters to find only the more perfect circles.
        circles = cv2.HoughCircles(gray_blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2, minDist=100,
                                   param1=100, param2=70,
                                   minRadius=50, maxRadius=0)

        best_candidate = None
        best_size_diff = float('inf')

        if circles is not None:
            circles = np.uint16(np.around(circles))
            # Iterate over all detected circles.
            for i in circles[0, :]:
                ball_u, ball_v, radius_pixels = i[0], i[1], i[2]
                measured_d_pixels = 2 * radius_pixels

                # Compute distance estimates.
                D_est = (f_avg * BALL_DIAMETER) / measured_d_pixels  # initial distance estimate in mm
                y_center_est = self.project_y(BALL_RADIUS_REAL, D_est, f_y, cy_img)
                y_contact_est = self.project_y(0, D_est, f_y, cy_img)
                delta = y_contact_est - y_center_est
                r_full = math.sqrt((measured_d_pixels / 2.0)**2 + delta**2)
                d_full = 2 * r_full
                D_corr = 2 * (f_avg * BALL_DIAMETER) / d_full  # corrected distance in mm

                # Compute expected diameter in pixels based on the corrected distance.
                expected_d_pixels = (f_avg * BALL_DIAMETER) / D_corr*math.sqrt(2)

                # Compare measured diameter with expected diameter.
                size_diff = abs(measured_d_pixels - expected_d_pixels)

                if size_diff < best_size_diff:
                    best_size_diff = size_diff
                    alpha = math.atan((ball_u - cx) / f_x)
                    beta = math.atan((self.project_y(BALL_RADIUS_REAL, D_corr, f_y, cy_img) - cy_img) / f_y)
                    effective_angle = CAMERA_TILT_RAD + beta
                    ground_distance = D_corr * math.cos(effective_angle)
                    X = ground_distance * math.sin(alpha)
                    Z = ground_distance * math.cos(alpha)
                    vertical_est = D_corr * math.sin(effective_angle)

                    best_candidate = {
                        "ball_u": ball_u,
                        "ball_v": ball_v,
                        "radius_pixels": radius_pixels,
                        "measured_d_pixels": measured_d_pixels,
                        "expected_d_pixels": expected_d_pixels,
                        "D_corr": D_corr,
                        "X": X,
                        "Z": Z,
                        "vertical_est": vertical_est
                    }
                    
        # If a candidate was found, annotate it.
        if best_candidate is not None:
            cv2.circle(frame, (best_candidate["ball_u"], best_candidate["ball_v"]), 3, (0, 255, 0), -1)
            cv2.circle(frame, (best_candidate["ball_u"], best_candidate["ball_v"]),
                       best_candidate["radius_pixels"], (0, 255, 0), 2)
            
            mask = np.zeros_like(gray)
            cv2.circle(mask, (best_candidate["ball_u"], best_candidate["ball_v"]),
                       best_candidate["radius_pixels"], 255, -1)
            mean_val = cv2.mean(frame, mask=mask)
            color_text = f"Color: B:{int(mean_val[0])} G:{int(mean_val[1])} R:{int(mean_val[2])}"
            
            lines = [
                f"Measured Diam: {best_candidate['measured_d_pixels']}px",
                f"Expected Diam: {best_candidate['expected_d_pixels']:.1f}px",
                f"Img Center: ({best_candidate['ball_u']}, {best_candidate['ball_v']})",
                f"Pos: X={best_candidate['X']:.1f}mm, Z={best_candidate['Z']:.1f}mm",
                f"Vert: {best_candidate['vertical_est']:.1f}mm (exp ~{CAMERA_HEIGHT - BALL_RADIUS_REAL}mm)",
                f"D: {best_candidate['D_corr']:.1f}mm",
                color_text
            ]
            self.draw_centered_text(frame, lines, best_candidate["ball_u"], best_candidate["ball_v"])

        # Compute and overlay FPS.
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - self.prev_frame_time)
        self.prev_frame_time = new_frame_time
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Rescale the image to a lower resolution before encoding.
        low_res_frame = cv2.resize(frame, (480, 360))
        
        # Encode the resized frame as JPEG with quality 50.
        ret, buffer = cv2.imencode('.jpg', low_res_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return "data:image/jpeg;base64,{}".format(jpg_as_text)
