function runRef()
% Regenerate reference_data/ref_*.mat from the original Simulink models.
% Run from the Matlab_Simulation folder (needs Simulink + Simscape Electrical):
%   >> runRef
InitZumo; vars=who; for i=1:numel(vars), assignin('base',vars{i},eval(vars{i})); end
sq=[0 0.5; 0.5 0.5; 0.5 0; 0 0]; ln=([0.2:0.2:2].*[0;1])';
cases = {'line',ln,'ZumoSimulatiom_Path_Control',40; 'line',ln,'ZumoSimulatiom_P2P_MultiPoint',40;
         'square',sq,'ZumoSimulatiom_Path_Control',40; 'square',sq,'ZumoSimulatiom_P2P_MultiPoint',40;
         'inf',infPts(),'ZumoSimulatiom_Path_Control',60; 'inf',infPts(),'ZumoSimulatiom_P2P_MultiPoint',60};
for c=1:size(cases,1)
  [nm,pts,mdl,T]=cases{c,:}; load_system(mdl);
  assignin('base','DesiredCoordinates',pts); set_param([mdl '/Desired Points'],'Value','DesiredCoordinates');
  logOn(mdl);
  out = sim(mdl,'StopTime',num2str(T),'SignalLogging','on','SignalLoggingName','logsout','ReturnWorkspaceOutputs','on');
  S = exportLogs(out.logsout); S.pts=pts;
  save(sprintf('ref_%s_%s.mat',strrep(mdl,'ZumoSimulatiom_',''),nm),'-struct','S'); close_system(mdl,0);
end
% open loop motor characterization (motor PI bypassed, constant duty)
mdl='ZumoSimulatiom_Path_Control'; load_system(mdl);
assignin('base','DesiredCoordinates',[0 50; 0 100]); set_param([mdl '/Desired Points'],'Value','DesiredCoordinates');
for s={'Left','Right'}, set_param([mdl '/DC Motor Simulation ' s{1} '/Manual Switch1'],'sw','0'); end
logOn(mdl); U=[0.05 0.1 0.2 0.3 0.4 0.5 0.6 0.8 1.0]; OL=struct();
for k=1:numel(U)
  for s={'Left','Right'}, set_param([mdl '/DC Motor Simulation ' s{1} '/Open Loop Constant'],'Value',num2str(U(k))); end
  out = sim(mdl,'StopTime','3','SignalLogging','on','SignalLoggingName','logsout','ReturnWorkspaceOutputs','on');
  OL.(sprintf('u%03d',round(U(k)*100)))=exportLogs(out.logsout);
end
OL.U=U; save('ref_openloop.mat','-struct','OL'); close_system(mdl,0);
end

function P=infPts()
t = -pi/2:0.1:pi*3/2; P=[cos(t)*0.5; cos(t).*sin(t)*0.5]'; P = P(2:end,:);
end

function logOn(mdl)
pc = find_system(mdl,'SearchDepth',1,'Regexp','on','Name','Path Control|Point to Point Control');
lst = {pc{1},1:5; [mdl '/Encoder Position Estimation'],1:3; [mdl '/Saturation'],1;
  [mdl '/DC Motor Simulation Left'],1; [mdl '/DC Motor Simulation Right'],1;
  [mdl '/Discrete PID Controller'],1; [mdl '/Discrete PID Controller1'],1;
  [mdl '/m//s->rads'],1; [mdl '/m//s->rads1'],1; [mdl '/Rate Limiter'],1};
for i=1:size(lst,1)
  ph=get_param(lst{i,1},'PortHandles');
  for p=lst{i,2}
    if p<=numel(ph.Outport)
      set_param(ph.Outport(p),'DataLogging','on','DataLoggingNameMode','Custom', ...
        'DataLoggingName',matlab.lang.makeValidName(sprintf('%s_%d',get_param(lst{i,1},'Name'),p)));
    end
  end
end
end

function S=exportLogs(ls)
S=struct();
for i=1:ls.numElements
  e=ls.getElement(i); v=e.Values; n=matlab.lang.makeValidName(e.Name);
  S.([n '_t'])=v.Time; S.(n)=squeeze(v.Data);
end
end
