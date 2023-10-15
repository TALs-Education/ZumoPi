
% generate the shape of infinity
t = [-pi/2 : 0.1 : pi*3/2];
X = cos(t)*0.5;
Y = cos(t).*sin(t)*0.5;

plot(X,Y)
hold on
plot(X,Y,'.')
hold off

% calculate pendicular vector and add the pen offset
Xdot = -sin(t);
Ydot = cos(t).^2 - sin(t).^2;
VPen(1,1:2) = [0 , 0];
Car(1,1:2) = [0 , 0];
for i = 1:size(X,2)
    VPen(i,1:2) = [-Ydot(i) , Xdot(i)]./sqrt(Ydot(i)^2 + Xdot(i)^2);
    Car(i,1:2) = [X(i) , Y(i)] + VPen(i,1:2).*0.05;
end 

hold on
plot(Car(:,1),Car(:,2))
%plot(VPen(:,1),VPen(:,2))
hold off

disp(Car);
disp(atan(Ydot(1)/Xdot(1))*180/pi);

