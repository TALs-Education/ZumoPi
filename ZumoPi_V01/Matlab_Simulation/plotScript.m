% [0 0.2 ;  0 0.4 ; 0 0.6; 0 0.8; 0 1]

% generate the shape of infinity
% t = [-pi/2 : 0.1 : pi*3/2];
% X = cos(t)*0.5;
% Y = cos(t).*sin(t)*0.5;
% DesiredCoordinates = ([X ; Y])';

% line coordinates
DesiredCoordinates =([0.2:0.2:2].*[0 ; 1])';

% run simulations and plot the responses
sim('ZumoSimulatiom_P2P_MultiPoint',30)
sim('ZumoSimulatiom_Path_Control',30)
disp("plot")
figure(1)
plot(Record_P2P.signals.values(:,1),Record_P2P.signals.values(:,2))
hold on
plot(Record_Path.signals.values(:,1),Record_Path.signals.values(:,2))
plot(DesiredCoordinates(:,1),DesiredCoordinates(:,2),"*")
hold off
legend P2P Path
grid on
title ('Path Control')
xlabel ('XPos [m]')
ylabel ('YPos [m]')