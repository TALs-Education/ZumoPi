#!/usr/bin/python3
import threading
import serial
import time
import math
import signal
import numpy as np
from collections import deque

# Dash imports
import dash
import dash_daq as daq
from dash import html
import dash_core_components as dcc
import plotly.graph_objs as go

# ZumoController class
class ZumoController:
    def __init__(self, serial_port):
        self.ser = serial.Serial(serial_port)
        self.zumo_angle = 0
        self.zumo_speed = 0
        self.closing_event = threading.Event()
        self.transmit_thread = threading.Thread(target=self.transmit_data)
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.lock = threading.Lock()
        # Open a file to save the incoming messages
        self.incoming_messages_file = open('incoming_messages.txt', 'a')
        self.last_messages = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def start(self):
        self.transmit_thread.start()
        self.receive_thread.start()

    def transmit_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            with self.lock:
                zumo_angle = self.zumo_angle if self.zumo_angle is not None else 0
                zumo_speed = self.zumo_speed if self.zumo_speed is not None else 0

            joy_y = math.sin(math.radians(zumo_angle)) * zumo_speed * 200
            joy_x = math.cos(math.radians(zumo_angle)) * zumo_speed * 200

            msg = f'{joy_x},{joy_y}\r\n'
            self.ser.write(msg.encode('ascii'))
            time.sleep(0.1)

    def receive_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            if self.ser.in_waiting > 0:
                c = self.ser.readline().decode("ascii")
                with self.lock:
                    self.incoming_messages_file.write(c)
                    self.last_messages.append(c.strip())
                    if len(self.last_messages) > 5:
                        self.last_messages.pop(0)
                print(c)
            else:
                time.sleep(0.05)

    def signal_handler(self, sig, frame, dash_app_thread):
        print("Closing the application.")
        self.close()
        dash_app_thread.join()

    def set_zumo_angle(self, angle):
        self.zumo_angle = angle if isinstance(angle, (int, float)) else 0

    def set_zumo_speed(self, speed):
        self.zumo_speed = speed if isinstance(speed, (int, float)) else 0

    def get_last_messages(self):
        return self.last_messages

    def close(self):
        self.closing_event.set()
        self.incoming_messages_file.close()

# ZumoDashApp class
class ZumoDashApp:
    def __init__(self, external_stylesheets, zumo_controller):
        self.zumo_controller = zumo_controller
        self.received_values = deque(maxlen=500)
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        self.create_layout()

    def create_layout(self):
        self.app.layout = html.Div([
            daq.Joystick(
                id='my-joystick',
                label="Zumo Joystick",
                angle=0,
                size=500
            ),
            html.Div(id='joystick-output'),
            html.Div(id='incoming-messages'),
            dcc.Graph(id='live-plot'),
            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # in milliseconds
                n_intervals=0
            )
        ])

    def update_output(self, angle, force):
        with self.zumo_controller.lock:
            self.zumo_controller.set_zumo_angle(angle)
            self.zumo_controller.set_zumo_speed(force)

        return [f'Angle is {angle}',
                html.Br(),
                f'Force is {force}']

    def update_incoming_messages(self, _):
        with self.zumo_controller.lock:
            last_messages = self.zumo_controller.get_last_messages()
        return html.Div([html.P(message) for message in last_messages])


    def update_plot(self, n_intervals):
        with self.zumo_controller.lock:
            last_messages = self.zumo_controller.get_last_messages()

        if last_messages:
            values = last_messages[-1].split(',')
            values = list(map(float, values))
            self.received_values.append(values)

        data = np.array(self.received_values).T

        return {
            'data': [
                go.Scatter(
                    x=list(range(len(data[0]))),
                    y=data[i],
                    mode='lines',
                    name=f'value{i+1}'
                ) for i in range(len(data))
            ],
            'layout': go.Layout(
                xaxis=dict(range=[0, len(data[0])]),
                yaxis=dict(range=[min(min(d) for d in data), max(max(d) for d in data)]),
                title='Live Plot of Incoming Messages'
            )
        }

    def start(self):
        self.app.callback(
            dash.dependencies.Output('joystick-output', 'children'),
            [dash.dependencies.Input('my-joystick', 'angle'),
             dash.dependencies.Input('my-joystick', 'force')])(self.update_output)

        self.app.callback(
            dash.dependencies.Output('incoming-messages', 'children'),
            [dash.dependencies.Input('joystick-output', 'children')])(self.update_incoming_messages)

        self.app.callback(
            dash.dependencies.Output('live-plot', 'figure'),
            [dash.dependencies.Input('interval-component', 'n_intervals')])(self.update_plot)

        self.app.server.run(port=8500, host='0.0.0.0')

def main():
    with ZumoController('/dev/ttyACM0') as zumo_controller:
        zumo_dash_app = ZumoDashApp(['pydash\templates\bWLwgP.css'], zumo_controller)
        zumo_controller.start()

        dash_app_thread = threading.Thread(target=zumo_dash_app.start)
        dash_app_thread.start()

        signal.signal(signal.SIGINT, lambda sig, frame: zumo_controller.signal_handler(sig, frame, dash_app_thread))

        zumo_controller.transmit_thread.join()
        zumo_controller.receive_thread.join()
        dash_app_thread.join()

if __name__ == "__main__":
    main()