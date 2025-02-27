#!/usr/bin/python3
import threading
import serial
import time
import math
import json
import numpy as np
from collections import deque
import logging
import base64

# Suppress Flask/werkzeug HTTP request logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Dash imports
import dash
import dash_daq as daq
from dash import html
from dash import dcc
import plotly.graph_objs as go
from flask import request

# Picamera2 and OpenCV imports
from picamera2 import Picamera2
import cv2

# --------------------
# Global Camera & Object Parameters
# --------------------
CAMERA_HEIGHT = 85.0       # mm above the ground
CAMERA_TILT_DEG = 25.0     # Camera tilted downward by 25 degrees
CAMERA_TILT_RAD = math.radians(CAMERA_TILT_DEG)
HORIZONTAL_FOV_DEG = 102.0 # Horizontal field of view (degrees)
VERTICAL_FOV_DEG = 67.0    # Vertical field of view (degrees)

BALL_DIAMETER = 70.0       # mm (real-world diameter)
BALL_RADIUS_REAL = BALL_DIAMETER / 2.0  # 35 mm

# --------------------
# Utility Functions for Image Processing
# --------------------
def project_y(Y_world, Z_world, f_y, cy):
    """
    Projects a world point (with vertical coordinate Y_world and ground distance Z_world)
    to an image vertical coordinate.
    """
    Y_rel = CAMERA_HEIGHT - Y_world  # positive if point is below the camera
    Y_cam = math.cos(CAMERA_TILT_RAD) * Y_rel - math.sin(CAMERA_TILT_RAD) * Z_world
    Z_cam = math.sin(CAMERA_TILT_RAD) * Y_rel + math.cos(CAMERA_TILT_RAD) * Z_world
    return f_y * (Y_cam / Z_cam) + cy

def draw_centered_text(img, lines, center_x, center_y, font=cv2.FONT_HERSHEY_SIMPLEX, 
                       font_scale=0.5, thickness=2, line_spacing=5, color=(0,255,255)):
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

# --------------------
# Main Application Class
# --------------------
class ZumoApp:
    def __init__(self, serial_port, external_stylesheets):
        # Open the serial port with the proper baud rate.
        self.ser = serial.Serial(serial_port, 115200)
        self.zumo_angle = 0
        self.zumo_speed = 0
        self.closing_event = threading.Event()
        self.transmit_thread = threading.Thread(target=self.transmit_data)
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.lock = threading.Lock()
        self.last_messages = []
        # Limit plot data to the last 100 measurements.
        self.received_values = deque(maxlen=100)
        # For FPS calculation.
        self.prev_frame_time = time.time()

        # Initialize Picamera2 with a reduced resolution.
        self.picam2 = Picamera2()
        preview_config = self.picam2.create_preview_configuration({"format": "RGB888", "size": (480, 360)})
        self.picam2.configure(preview_config)
        self.picam2.start()

        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        self.create_layout()

        self.file = open('recorded_messages.txt', 'a')

    def start(self):
        self.transmit_thread.start()
        self.receive_thread.start()
        self.app.run_server(port=8500, host='0.0.0.0', debug=False, use_reloader=False)

    def transmit_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            with self.lock:
                # Compute joystick components based on current angle and force.
                joy_y = math.sin(math.radians(self.zumo_angle)) * self.zumo_speed * 200
                joy_x = math.cos(math.radians(self.zumo_angle)) * self.zumo_speed * 200
            left_velocity = joy_y + joy_x
            right_velocity = joy_y - joy_x
            command = {"vl": left_velocity, "vr": right_velocity}
            msg = json.dumps(command) + "\n"
            self.ser.write(msg.encode('ascii'))
            # (Console messages commented out)
            # print("Sent:", msg.strip())
            time.sleep(0.1)

    def receive_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            if self.ser.in_waiting > 0:
                c = self.ser.readline().decode("ascii").strip()
                with self.lock:
                    self.last_messages.append(c)
                    if len(self.last_messages) > 3:
                        self.last_messages.pop(0)
                # (Console messages commented out)
                # print("Received:", c)
                self.file.write(c + "\n")
            else:
                time.sleep(0.05)

    def create_layout(self):
        # Layout: video stream on the left, joystick on the right; plot below.
        self.app.layout = html.Div([
            html.Button("Close", id="close-button", style={'width': '100%'}),
            html.Div([
                # Left: Live camera stream.
                html.Div([
                    html.Img(id="live-image", style={'width': '480px', 'height': '360px'})
                ], style={'flex': '1', 'padding': '10px'}),
                # Right: Joystick control.
                html.Div([
                    daq.Joystick(id='my-joystick', label="Zumo Joystick", angle=0, size=300),
                    html.Div(id='joystick-output', style={'marginTop': '10px'})
                ], style={'flex': '1', 'padding': '10px'}),
            ], style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
            # Live plot.
            html.Div([
                dcc.Graph(id='live-plot', style={'height': '300px'})
            ]),
            dcc.Interval(id='interval-component', interval=500, n_intervals=0),
            html.Div(id='hidden-div', style={'display': 'none'})
        ])

        self.app.callback(
            dash.dependencies.Output('joystick-output', 'children'),
            [dash.dependencies.Input('my-joystick', 'angle'),
             dash.dependencies.Input('my-joystick', 'force')]
        )(self.update_joystick)

        # Callback to update the live camera stream image.
        self.app.callback(
            dash.dependencies.Output('live-image', 'src'),
            [dash.dependencies.Input('interval-component', 'n_intervals')]
        )(self.update_image)

        self.app.callback(
            dash.dependencies.Output('live-plot', 'figure'),
            [dash.dependencies.Input('interval-component', 'n_intervals')]
        )(self.update_plot)
         
        self.app.callback(
            dash.dependencies.Output('hidden-div', 'children'),
            [dash.dependencies.Input('close-button', 'n_clicks')]
        )(self.close_button_clicked)

    def update_joystick(self, angle, force):
        with self.lock:
            self.zumo_angle = angle if isinstance(angle, (int, float)) else 0
            self.zumo_speed = force if isinstance(force, (int, float)) else 0
        return [f'Angle is {angle}', html.Br(), f'Force is {force}']

    def update_image(self, n_intervals):
        # Capture a frame from the camera.
        frame = self.picam2.capture_array()
        height, width, _ = frame.shape

        # Calculate intrinsic parameters.
        cx = width / 2.0
        cy_img = height / 2.0
        f_x = (width / 2.0) / math.tan(math.radians(HORIZONTAL_FOV_DEG / 2.0))
        f_y = (height / 2.0) / math.tan(math.radians(VERTICAL_FOV_DEG / 2.0))
        f_avg = (f_x + f_y) / 2.0

        # Preprocess for circle detection.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(gray_blurred, cv2.HOUGH_GRADIENT,
                                   dp=1.2, minDist=100,
                                   param1=100, param2=30,
                                   minRadius=50, maxRadius=0)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                ball_u, ball_v, radius_pixels = i[0], i[1], i[2]
                # Draw the detected circle and its center.
                cv2.circle(frame, (ball_u, ball_v), 3, (0, 255, 0), -1)
                cv2.circle(frame, (ball_u, ball_v), radius_pixels, (0, 255, 0), 2)
                
                measured_d_pixels = 2 * radius_pixels
                D_est = (f_avg * BALL_DIAMETER) / measured_d_pixels  # in mm
                y_center_est = project_y(BALL_RADIUS_REAL, D_est, f_y, cy_img)
                y_contact_est = project_y(0, D_est, f_y, cy_img)
                delta = y_contact_est - y_center_est
                r_full = math.sqrt((measured_d_pixels / 2.0)**2 + delta**2)
                d_full = 2 * r_full
                D_corr = 2 * (f_avg * BALL_DIAMETER) / d_full
                y_center_corr = project_y(BALL_RADIUS_REAL, D_corr, f_y, cy_img)
                alpha = math.atan((ball_u - cx) / f_x)
                beta = math.atan((y_center_corr - cy_img) / f_y)
                effective_angle = CAMERA_TILT_RAD + beta
                ground_distance = D_corr * math.cos(effective_angle)
                X = ground_distance * math.sin(alpha)
                Z = ground_distance * math.cos(alpha)
                vertical_est = D_corr * math.sin(effective_angle)
                
                # Compute average color inside the detected circle.
                mask = np.zeros_like(gray)
                cv2.circle(mask, (ball_u, ball_v), radius_pixels, 255, -1)
                mean_val = cv2.mean(frame, mask=mask)
                color_text = f"Color: B:{int(mean_val[0])} G:{int(mean_val[1])} R:{int(mean_val[2])}"
                
                lines = [
                    f"Diam (pix): {measured_d_pixels}px",
                    f"Img Center: ({ball_u}, {ball_v})",
                    f"Pos: X={X:.1f}mm, Z={Z:.1f}mm",
                    f"Vert: {vertical_est:.1f}mm (exp ~{CAMERA_HEIGHT - BALL_RADIUS_REAL}mm)",
                    f"D: {D_corr:.1f}mm",
                    color_text
                ]
                draw_centered_text(frame, lines, ball_u, ball_v, font_scale=0.5, thickness=2, line_spacing=5)
                break  # Process only the first detected ball.
        
        # Compute and overlay FPS.
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - self.prev_frame_time)
        self.prev_frame_time = new_frame_time
        overlay_text = f"Res: {width}x{height} | FPS: {fps:.2f}"
        cv2.putText(frame, overlay_text, (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Encode the processed frame as JPEG.
        ret, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        src = "data:image/jpeg;base64,{}".format(jpg_as_text)
        return src

    def update_plot(self, n_intervals):
        if self.closing_event.is_set():
            raise dash.exceptions.PreventUpdate

        try:
            with self.lock:
                last_messages = self.last_messages.copy()

            if last_messages:
                try:
                    data_msg = json.loads(last_messages[-1])
                    left_velocity = data_msg.get("vL", 0)
                    right_velocity = data_msg.get("vR", 0)
                    values = [left_velocity, right_velocity]
                except Exception:
                    try:
                        values = list(map(float, last_messages[-1].split(',')))
                    except Exception:
                        values = [0, 0]
                self.received_values.append(values)

            if self.received_values:
                data = np.array(self.received_values).T
                variable_names = ["vL", "vR"]
                traces = [
                    go.Scatter(
                        x=list(range(len(data[0]))),
                        y=data[i],
                        mode='lines',
                        name=variable_names[i] if i < len(variable_names) else f'value{i+1}'
                    ) for i in range(len(data))
                ]
                layout = go.Layout(
                    xaxis=dict(range=[0, len(data[0])]),
                    yaxis=dict(range=[min(min(d) for d in data), max(max(d) for d in data)]),
                    title='Live Plot of Incoming Messages'
                )
            else:
                traces = []
                layout = go.Layout(title='Live Plot of Incoming Messages')
            return {'data': traces, 'layout': layout}
        except Exception as e:
            logging.error("Error in update_plot: %s", e)
            return {'data': [], 'layout': go.Layout(title='Live Plot Error')}

    def close(self): 
        self.closing_event.set()
        self.file.close()
        self.picam2.stop()

    def close_button_clicked(self, n_clicks):
        if n_clicks is not None and n_clicks > 0:
            self.close()
            time.sleep(1)
            self.stop()

    def stop(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

def main():
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    serial_port = '/dev/ttyAMA10'
    zumo_app = ZumoApp(serial_port, external_stylesheets)

    try:
        zumo_app.start()
    except KeyboardInterrupt:
        print("Ctrl+C detected, stopping the application.")
        zumo_app.close()

if __name__ == "__main__":
    main()
