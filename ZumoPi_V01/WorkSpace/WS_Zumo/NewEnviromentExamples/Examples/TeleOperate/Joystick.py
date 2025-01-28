#!/usr/bin/python3
import threading
import serial
import time
import math

#dash imports
import dash
import dash_daq as daq
#import dash_html_components as html
from dash import html
import logging

external_stylesheets = ['pydash\templates\bWLwgP.css']

# serial connection
ser = serial.Serial('/dev/ttyACM0')  # open serial port

# variables
global zumoAngle, zumoSpeed


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)



app.layout = html.Div([
    daq.Joystick(
        id='my-joystick',
        label="Zumo Joystick",
        angle=0,
        size = 500
    ),
    html.Div(id='joystick-output')
])

@app.callback(
    dash.dependencies.Output('joystick-output', 'children'),
    [dash.dependencies.Input('my-joystick', 'angle'),
     dash.dependencies.Input('my-joystick', 'force')])
def update_output(angle, force):
    global zumoSpeed, zumoAngle
    if type(angle) == int or float:
      zumoAngle = angle
    else:
      zumoAngle = 0
    if type(force) == int or float:
      zumoSpeed = force
    else:
      zumoSpeed = 0 
    #print("speed {:.2f} Angle {:.2f}".format(zumoSpeed,zumoAngle))
    return ['Angle is {}'.format(angle),
            html.Br(),
            'Force is {}'.format(force)]

def start_app():
    app.server.run(port=8500, host='0.0.0.0')
 
def TransmitThread(counter):
  while ser.isOpen:
    #print("send data")
    global zumoSpeed, zumoAngle
    if zumoAngle is None:
      zumoAngle = 0
    if zumoSpeed is None:
      zumoSpeed = 0 
    joyY = math.sin(math.radians(zumoAngle))*zumoSpeed*200
    joyX = math.cos(math.radians(zumoAngle))*zumoSpeed*200
    #print(f'joystick {joyX}\t{joyY}')
    msg = ''
    msg = str(joyX) + ',' +str(joyY) +'\r\n'
    ser.write(msg.encode('ascii'))
    time.sleep(0.1)

def ReceiveThread():
  while ser.isOpen:
    if ser.in_waiting > 0:
      #print("recived data")
      #c = ser.read(ser.in_waiting)
      c = ser.readline().decode("ascii")
      print(c)
    else:
      time.sleep(0.05)
 
def initializeThreads():
  global zumoAngle, zumoSpeed
  counter = 0
  zumoAngle = 0 
  zumoSpeed = 0
  # supress logging
  log = logging.getLogger('werkzeug')
  log.setLevel(logging.ERROR)
  
  #define threads, and start them
  t1 = threading.Thread(target=TransmitThread,args=(counter,))
  t2 = threading.Thread(target=ReceiveThread)
  t3 = threading.Thread(target=start_app)   
  t1.start()
  t2.start()
  t3.start()
          
if __name__ == "__main__":
  initializeThreads()
    
    
    