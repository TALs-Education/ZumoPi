% Start up script for the ZumoSimulation ZumoSimulatiom.slx
% declare variables for the simulation
sampleTime = 0.01; % Simulation Sample time in seconds

%Platform charasteristics:
GearRatio = 75;
WheelRadius=7.5/2/100;
Robot_L=36/100;

%Motor parameters:
%Max rotation velocity of a wheel w[rad/sec]=2*pi*w[rotation/sec]
w_Max=33000/60*2*pi; %[rad/sec] %motor datasheet 33000 rotation/minute
%w_Max=12000;
v_Max=w_Max/GearRatio*WheelRadius; %[m/s] %V=2*pi*w (w -  rotation/sec)
%Max acceleration
a_Max=1; %[m/s^2]
%Max rotation acceleration
wdot_Max=a_Max*GearRatio/WheelRadius; %[rad/sec^2]

% Initial State variables:
Phi_Init=0;
X_Pos_Init=0;
Y_Pos_Init=0;