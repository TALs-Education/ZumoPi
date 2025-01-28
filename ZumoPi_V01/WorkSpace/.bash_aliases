#arduino cli
alias compileuno="arduino-cli compile --fqbn arduino:avr:uno"
alias uploaduno="arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno"
alias compilezumo="arduino-cli compile --fqbn pololu-a-star:avr:a-star32U4"
alias uploadzumo="arduino-cli upload -p /dev/ttyACM0 --fqbn pololu-a-star:avr:a-star32U4"

alias zumoPower="sudo python3 /home/pi/x728/x728bat.py"
alias zumoCamera="sudo python3 /home/pi/WS_Zumo/Examples/PiCamera/CameraStream.py"
alias zumoJoystick="python3 /home/pi/WS_Zumo/Examples/TeleOperate/Joystick.py"