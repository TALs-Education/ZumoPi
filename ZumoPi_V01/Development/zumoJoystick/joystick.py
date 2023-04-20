#!/usr/bin/python3
import threading
import serial
import time
import math
import signal

# Dash imports
import dash
import dash_daq as daq
from dash import html
import logging

external_stylesheets = ['pydash\templates\bWLwgP.css']

# ZumoController class
class ZumoController:
    def __init__(self, serial_port):
        self.ser = serial.Serial(serial_port)
        self.zumo_angle = 0
        self.zumo_speed = 0
        self.closing_event = threading.Event()

        # Open a file to save the incoming messages
        self.incoming_messages_file = open('incoming_messages.txt', 'a')

        self.transmit_thread = threading.Thread(target=self.transmit_data)
        self.receive_thread = threading.Thread(target=self.receive_data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def start(self):
        self.transmit_thread.start()
        self.receive_thread.start()

    def transmit_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            self.zumo_angle = self.zumo_angle if self.zumo_angle is not None else 0
            self.zumo_speed = self.zumo_speed if self.zumo_speed is not None else 0

            joy_y = math.sin(math.radians(self.zumo_angle)) * self.zumo_speed * 200
            joy_x = math.cos(math.radians(self.zumo_angle)) * self.zumo_speed * 200

            msg = f'{joy_x},{joy_y}\r\n'
            self.ser.write(msg.encode('ascii'))
            time.sleep(0.1)

    def receive_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            if self.ser.in_waiting > 0:
                c = self.ser.readline().decode("ascii")
                self.incoming_messages_file.write(c)  # Save the message to the file
                print(c)
            else:
                time.sleep(0.05)

    def signal_handler(self, sig, frame, dash_app_thread):
        print("Closing the application.")
        self.close()
        dash_app_thread.join()

    def close(self):
        self.closing_event.set()
        self.incoming_messages_file.close()  # Close the file

# ZumoDashApp class
class ZumoDashApp:
    def __init__(self, external_stylesheets):
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
            html.Div(id='joystick-output')
        ])

    def update_output(self, angle, force):
        global zumo_controller
        zumo_controller.zumo_angle = angle if isinstance(angle, (int, float)) else 0
        zumo_controller.zumo_speed = force if isinstance(force, (int, float)) else 0

        return ['Angle is {}'.format(angle),
                html.Br(),
                'Force is {}'.format(force)]

    def start(self):
        self.app.callback(
            dash.dependencies.Output('joystick-output', 'children'),
            [dash.dependencies.Input('my-joystick', 'angle'),
             dash.dependencies.Input('my-joystick', 'force')])(self.update_output)
        self.app.server.run(port=8500, host='0.0.0.0')

def main():
    with ZumoController('/dev/ttyACM0') as zumo_controller:
        zumo_dash_app = ZumoDashApp(external_stylesheets)
        zumo_controller.start()

        dash_app_thread = threading.Thread(target=zumo_dash_app.start)
        dash_app_thread.start()

        signal.signal(signal.SIGINT, lambda sig, frame: zumo_controller.signal_handler(sig, frame, dash_app_thread))

        zumo_controller.transmit_thread.join()
        zumo_controller.receive_thread.join()
        dash_app_thread.join()

if __name__ == "__main__":
    main()
