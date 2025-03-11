% acceleration profile
samples = 150;
amax= 0.4;
a = [ones(1,samples/3)*amax zeros(1,samples/3) -ones(1,samples/3)*amax];
t = [0:(size(a,2)-1)]*0.02;
v = zeros(1,samples);
s = zeros(1,samples);
for i = 1: size(t,2)-1
    v(i) = sum(a(1:i).*diff(t(1:i+1)));
    s(i) = sum(v(1:i).*diff(t(1:i+1)));
end
s(end) = s(end-1);

% plot
%  plot(t,a,'*') 
%  hold on
%  plot(t,v,'*') 
%  plot(t,s,'*') 

 figure(1)
 plot(t,a,'r') 
 hold on
 plot(t,v,'g') 
 plot(t,s,'b') 
 grid on
 legend("acceleration" , "velocity" , "distance")
 xlabel("time")

 figure(2)
 plot(s,v,'g')
 grid on
 hold on 
 plot(s,a,'r')
 legend("velocity" , "acceleration")
 xlabel("distance")

