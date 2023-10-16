% Start up script for the ZumoSimulation ZumoSimulatiom.slx
% declare variables for the simulation
sampleTime = 0.01; % Simulation Sample time in seconds

%Platform charasteristics:
GearRatio = 75;
WheelRadius=37.5/2/1000;    % [m]
Robot_L=98/1000;            % [m]

%Max linear acceleration / Velocity
a_Max = 1/8; %[m/s^2]
v_Max = 1/4; %[m/s]

%Max Wheels acceleration / Velocity
wdot_Max=a_Max/(WheelRadius*2*pi); %[rad/sec^2] a=2*pi*r*w_dot (w -  rotation/sec)
w_Max=v_Max/(WheelRadius*2*pi); %[rad/sec^2] V=2*pi*r*w (w -  rotation/sec)

% Initial State variables:
Phi_Init=0;
X_Pos_Init=0;
Y_Pos_Init=0;