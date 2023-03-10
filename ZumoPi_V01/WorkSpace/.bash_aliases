# shut down ups
alias x728off='sudo x728softsd.sh'

#arduino cli
alias compileuno="arduino-cli compile --fqbn arduino:avr:uno"
alias uploaduno="arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno"
alias compilezumo="arduino-cli compile --fqbn pololu-a-star:avr:a-star32U4"
alias uploadzumo="arduino-cli upload -p /dev/ttyACM0 --fqbn pololu-a-star:avr:a-star32U4"

alias zumoPower="python x728bat.py"
alias zumoRemote="python3 /home/pi/WS_Zumo/Arduino/TeleOperate/KeyboardTeleoperate.py"
alias zumoCamera="python3 /home/pi/WS_Zumo/PiCamera/CameraStream.py"
alias zumoJoystick="python3 /home/pi/WS_Zumo/DashControl/myJoystick.py"