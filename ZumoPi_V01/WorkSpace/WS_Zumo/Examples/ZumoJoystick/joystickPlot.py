#!/usr/bin/python3
import threading
import serial
import time
import math
import numpy as np
from collections import deque

# Dash imports
import dash
import dash_daq as daq
from dash import html
from dash import dcc
import plotly.graph_objs as go
from flask import request

# ZumoApp class
class ZumoApp:
    def __init__(self, serial_port, external_stylesheets):
        self.ser = serial.Serial(serial_port)
        self.zumo_angle = 0
        self.zumo_speed = 0
        self.closing_event = threading.Event()
        self.transmit_thread = threading.Thread(target=self.transmit_data)
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.lock = threading.Lock()
        self.last_messages = []

        self.received_values = deque(maxlen=500)
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        self.create_layout()

    def start(self):
        self.transmit_thread.start()
        self.receive_thread.start()
        self.app.run_server(port=8500, host='0.0.0.0')

    def transmit_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            with self.lock:
                joy_y = math.sin(math.radians(self.zumo_angle)) * self.zumo_speed * 200
                joy_x = math.cos(math.radians(self.zumo_angle)) * self.zumo_speed * 200

            msg = f'{joy_x},{joy_y}\r\n'
            self.ser.write(msg.encode('ascii'))
            time.sleep(0.1)

    def receive_data(self):
        while not self.closing_event.is_set() and self.ser.isOpen:
            if self.ser.in_waiting > 0:
                c = self.ser.readline().decode("ascii")
                with self.lock:
                    self.last_messages.append(c.strip())
                    if len(self.last_messages) > 3:
                        self.last_messages.pop(0)
                print(c)
            else:
                time.sleep(0.05)

    def create_layout(self):
        self.app.layout = html.Div([
            html.Button("Close", id="close-button", style={'width': '100%'}),
            html.Div([    html.Div([        daq.Joystick(id='my-joystick', label="Zumo Joystick", angle=0, size=250),    ], style={'flex': '1'}),
                html.Div([        html.Div(id='joystick-output'),        html.Div(id='incoming-messages', style={'marginTop': '10px'}),    ], style={'flex': '1'}),
            ], style={
                'display': 'flex',
                'justify-content': 'center',
                'align-items': 'center',
            }),
            dcc.Graph(id='live-plot'),
            dcc.Interval(id='interval-component', interval=0.1*1000, n_intervals=0),
            html.Div(id='hidden-div', style={'display': 'none'})  # Hidden div for the close button callback

        ])

        self.app.callback(dash.dependencies.Output('joystick-output', 'children'),
                          [dash.dependencies.Input('my-joystick', 'angle'),
                           dash.dependencies.Input('my-joystick', 'force')])(self.update_output)

        self.app.callback(dash.dependencies.Output('incoming-messages', 'children'),
                          [dash.dependencies.Input('joystick-output', 'children')])(self.update_incoming_messages)

        self.app.callback(dash.dependencies.Output('live-plot', 'figure'),
                          [dash.dependencies.Input('interval-component', 'n_intervals')])(self.update_plot)
         
        self.app.callback(dash.dependencies.Output('hidden-div', 'children'),
                          [dash.dependencies.Input('close-button', 'n_clicks')])(self.close_button_clicked)

    def update_output(self, angle, force):
        with self.lock:
            self.zumo_angle = angle if isinstance(angle, (int, float)) else 0
            self.zumo_speed = force if isinstance(force, (int, float)) else 0

        return [f'Angle is {angle}',
                html.Br(),
                f'Force is {force}']
    
    def update_incoming_messages(self, _):
        with self.lock:
            last_messages = self.last_messages
        return html.Div([html.P(message) for message in last_messages])

    def update_plot(self, n_intervals):
        if self.closing_event.is_set():  # Check if closing_event is set
            raise dash.exceptions.PreventUpdate  # Prevent updating the plot if the event is set

        with self.lock:
            last_messages = self.last_messages

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

    def close(self):
        self.closing_event.set()

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
    serial_port = '/dev/ttyACM0'
    zumo_app = ZumoApp(serial_port, external_stylesheets)

    try:
        zumo_app.start()
    except KeyboardInterrupt:
        print("Ctrl+C detected, stopping the application.")
        zumo_app.close()

if __name__ == "__main__":
    main()