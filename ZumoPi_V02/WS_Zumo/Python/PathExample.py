#!/usr/bin/python3
import threading
import serial
import time
import json
import numpy as np
from collections import deque
import logging

# Suppress Flask/werkzeug HTTP request logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Dash imports
import dash
from dash import html, dcc
import plotly.graph_objs as go
from flask import request

class RobotApp:
    def __init__(self, serial_port, external_stylesheets):
        # Open the serial port (adjust your baud rate and timeout as needed)
        self.ser = serial.Serial(serial_port, 115200, timeout=0.1)

        # Event and thread management
        self.closing_event = threading.Event()
        self.receive_thread = threading.Thread(target=self.receive_data)

        # Lock for thread-safe access to shared data
        self.lock = threading.Lock()

        # Store incoming data as tuples of (X, Y, Theta, vL, vR)
        self.received_data = deque(maxlen=500)

        # Dash application
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        self.create_layout()

        # Log file (optional)
        self.file = open('recorded_messages.txt', 'a')

    def start(self):
        # Start thread(s)
        self.receive_thread.start()

        # Launch Dash
        self.app.run_server(port=8500, host='0.0.0.0', debug=False, use_reloader=False)

    def receive_data(self):
        """
        Continuously read and parse JSON data from the robot.
        Expected format example:
          {
             "X":123.45, 
             "Y":67.89,
             "Theta":45.67,
             "vL":12.34,
             "vR":56.78
          }
        """
        while not self.closing_event.is_set() and self.ser.isOpen:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                with self.lock:
                    self.file.write(line + "\n")  # record raw line to file (optional)
                    try:
                        data_msg = json.loads(line)
                        # Extract relevant fields, with defaults if missing
                        x = data_msg.get("X", 0.0)
                        y = data_msg.get("Y", 0.0)
                        theta = data_msg.get("Theta", 0.0)
                        vL = data_msg.get("vL", 0.0)
                        vR = data_msg.get("vR", 0.0)

                        self.received_data.append((x, y, theta, vL, vR))
                    except json.JSONDecodeError:
                        # If the line isn't valid JSON, just skip it
                        pass
            else:
                time.sleep(0.05)

    # If you need to transmit data to the robot (e.g., commands),
    # you can place that logic here. This example is read-only, so we omit it.
    # def transmit_data(self):
    #     while not self.closing_event.is_set() and self.ser.isOpen:
    #         command = {"some_command": 123}
    #         msg = json.dumps(command) + "\n"
    #         self.ser.write(msg.encode('ascii'))
    #         time.sleep(0.1)

    def create_layout(self):
        """
        Creates the Dash layout with:
          - A 'Close' button
          - Two Graph components: one for 2D path (X vs Y), one for time-series
          - A timed Interval for live updates
        """
        self.app.layout = html.Div([
            html.Button("Close", id="close-button", style={'width': '100%'}),

            html.Div([
                dcc.Graph(id='live-path'),
                dcc.Graph(id='live-vars'),
            ]),

            # Interval to trigger updates every 100 ms
            dcc.Interval(id='interval-component', interval=100, n_intervals=0),

            # Hidden div for shutting down the server
            html.Div(id='hidden-div', style={'display': 'none'})
        ])

        # Callbacks for updating plots
        self.app.callback(
            dash.dependencies.Output('live-path', 'figure'),
            dash.dependencies.Output('live-vars', 'figure'),
            [dash.dependencies.Input('interval-component', 'n_intervals')]
        )(self.update_plots)

        # Callback for close button
        self.app.callback(
            dash.dependencies.Output('hidden-div', 'children'),
            [dash.dependencies.Input('close-button', 'n_clicks')]
        )(self.close_button_clicked)

    def update_plots(self, n_intervals):
        """
        1) Plots (X,Y) as a path (scatter line).
        2) Plots Theta, vL, vR as time-series data.
        """
        if self.closing_event.is_set():
            raise dash.exceptions.PreventUpdate

        # Copy data under lock to avoid race conditions
        with self.lock:
            data_list = list(self.received_data)

        if len(data_list) == 0:
            # No data yet
            return go.Figure(), go.Figure()

        # Convert to numpy array for easy slicing
        # Each row: [X, Y, Theta, vL, vR]
        arr = np.array(data_list)
        x_vals = arr[:, 0]
        y_vals = arr[:, 1]
        theta_vals = arr[:, 2]
        vL_vals = arr[:, 3]
        vR_vals = arr[:, 4]

        # ------------------------------------------------------
        #  1) 2D Path Plot: X vs Y
        # ------------------------------------------------------
        path_trace = go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            name='Robot Path'
        )
        layout_path = go.Layout(
            title='2D Robot Path',
            #width=1200,
            height=1200,
            xaxis=dict(range=[-500, 500],
                    title='X (mm)'),
            yaxis=dict(range=[-500, 500],
                    title='Y (mm)',
                    scaleanchor='x',
                    scaleratio=1),
        )
        fig_path = go.Figure(data=[path_trace], layout=layout_path)

        # ------------------------------------------------------
        #  2) Time-Series Plot (Theta, vL, vR)
        # ------------------------------------------------------
        time_index = list(range(len(arr)))

        trace_theta = go.Scatter(
            x=time_index,
            y=theta_vals,
            mode='lines',
            name='Theta (deg)'
        )
        trace_vL = go.Scatter(
            x=time_index,
            y=vL_vals,
            mode='lines',
            name='vL (mm/s)'
        )
        trace_vR = go.Scatter(
            x=time_index,
            y=vR_vals,
            mode='lines',
            name='vR (mm/s)'
        )

        layout_vars = go.Layout(
            title='Time-Series of Theta, vL, vR',
            xaxis=dict(title='Sample Index'),
            yaxis=dict(title='Value')
        )
        fig_vars = go.Figure(data=[trace_theta, trace_vL, trace_vR], layout=layout_vars)

        return fig_path, fig_vars

    def close(self):
        # Signal the threads to close
        self.closing_event.set()
        self.file.close()

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
    # Update this port for your platform. Example: '/dev/ttyAMA10' on Raspberry Pi
    serial_port = '/dev/ttyAMA10'
    robot_app = RobotApp(serial_port, external_stylesheets)

    try:
        robot_app.start()
    except KeyboardInterrupt:
        print("Ctrl+C detected, stopping the application.")
        robot_app.close()

if __name__ == "__main__":
    main()
