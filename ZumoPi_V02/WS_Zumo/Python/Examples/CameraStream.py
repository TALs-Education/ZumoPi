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
        
        # Limit plot data to last 100 measurements.
        self.received_values = deque(maxlen=100)

        # Initialize Picamera2 with reduced resolution.
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

            # Simple mixing: left = joy_y + joy_x, right = joy_y - joy_x.
            left_velocity = joy_y + joy_x
            right_velocity = joy_y - joy_x

            # Pack velocities into JSON using keys 'vl' and 'vr'
            command = {"vl": left_velocity, "vr": right_velocity}
            msg = json.dumps(command) + "\n"
            self.ser.write(msg.encode('ascii'))
            # Console messages commented out:
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
                # Console messages commented out:
                # print("Received:", c)
                self.file.write(c + "\n")
            else:
                time.sleep(0.05)

    def create_layout(self):
        # Layout: stream on the left, joystick on the right.
        self.app.layout = html.Div([
            html.Button("Close", id="close-button", style={'width': '100%'}),
            html.Div([
                # Left: Live camera stream with reduced resolution.
                html.Div([
                    html.Img(id="live-image", style={'width': '480px', 'height': '360px'})
                ], style={'flex': '1', 'padding': '10px'}),
                # Right: Joystick control.
                html.Div([
                    daq.Joystick(id='my-joystick', label="Zumo Joystick", angle=0, size=250),
                    html.Div(id='joystick-output', style={'marginTop': '10px'})
                ], style={'flex': '1', 'padding': '10px'}),
            ], style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center'}),
            dcc.Graph(id='live-plot'),
            # Update interval (500ms)
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
        # Encode the frame as JPEG.
        ret, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        src = "data:image/jpeg;base64,{}".format(jpg_as_text)
        return src

    def update_plot(self, n_intervals):
        if self.closing_event.is_set():
            raise dash.exceptions.PreventUpdate

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
