InitZumo; mdl='Simplified_OpenLoop'; load_system(mdl);
ph=get_param([mdl '/Encoder Position Estimation'],'PortHandles');
for p=1:3, set_param(ph.Outport(p),'DataLogging','on','DataLoggingNameMode','Custom','DataLoggingName',sprintf('pos%d',p)); end
for s={'Left','Right'}, h=get_param([mdl '/DC Motor Simulation ' s{1}],'PortHandles'); set_param(h.Outport(1),'DataLogging','on','DataLoggingNameMode','Custom','DataLoggingName',['w' s{1}]); end
ms=find_system(mdl,'LookUnderMasks','all','BlockType','ManualSwitch'); for i=1:numel(ms), fprintf('%s sw=%s\n',ms{i},get_param(ms{i},'sw')); end
out=sim(mdl,'StopTime','30','SignalLogging','on','SignalLoggingName','logsout','ReturnWorkspaceOutputs','on');
S=struct(); for i=1:out.logsout.numElements, e=out.logsout.getElement(i); S.(e.Name)=squeeze(e.Values.Data); S.([e.Name '_t'])=e.Values.Time; end
S.pts=[-1 1]; save('ref_OpenLoop_point.mat','-struct','S'); disp('ok');
