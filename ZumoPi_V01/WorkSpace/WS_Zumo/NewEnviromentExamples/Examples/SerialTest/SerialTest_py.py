#!/usr/bin/python3
import threading
import serial
import time
# serial connection
ser = serial.Serial('/dev/ttyACM0')  # open serial port

def TransmitThread(counter):
  while ser.isOpen:
    #print("send data")
    counter+=1
    msg = 'test ' + str(counter) + '\r\n'
    ser.write(msg.encode('ascii'))
    time.sleep(1)

def ReceiveThread():
  while ser.isOpen:
    if ser.in_waiting > 0:
      #print("recived data")
      #c = ser.read(ser.in_waiting)
      c = ser.readline()
      print(c)
    else:
      time.sleep(0.1)

def LoopbackTest():
  counter = 0
  t1 = threading.Thread(target=TransmitThread,args=(counter,))
  t2 = threading.Thread(target=ReceiveThread)
  t1.start()
  t2.start()

  try:
    while True:
      time.sleep(1)
  except:
      pass

if __name__ == "__main__":
  LoopbackTest()