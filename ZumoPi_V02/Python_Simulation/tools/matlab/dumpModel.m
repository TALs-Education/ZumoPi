function dumpModel(mdl)
load_system(mdl);
fid = fopen([mdl '_dump.txt'],'w');
blks = find_system(mdl,'LookUnderMasks','all','FollowLinks','on','Type','Block');
skip = {'Name','Parent','Handle','Position','PortHandles','PortConnectivity','LineHandles','ObjectParameters','DialogParameters','IntrinsicDialogParameters','BlockType'};
for i=1:numel(blks)
  b = blks{i};
  bt = get_param(b,'BlockType');
  fprintf(fid,'\n### %s  [%s]\n', strrep(b,newline,' '), bt);
  try, dp = get_param(b,'DialogParameters'); catch, dp=[]; end
  if isstruct(dp)
    fn = fieldnames(dp);
    for k=1:numel(fn)
      try
        v = get_param(b,fn{k});
        if ischar(v) && numel(v)<300, fprintf(fid,'   %s = %s\n',fn{k},strrep(v,newline,' ')); end
      catch, end
    end
  end
  pc = get_param(b,'PortConnectivity');
  for p=1:numel(pc)
    src = pc(p).SrcBlock; dst = pc(p).DstBlock;
    if ~isempty(src) && src~=-1
      fprintf(fid,'   IN %s <- %s:%d\n', pc(p).Type, strrep(getfullname(src),newline,' '), pc(p).SrcPort+1);
    end
  end
end
fclose(fid);
end
