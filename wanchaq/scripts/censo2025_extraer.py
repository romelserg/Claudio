import openpyxl,sys,json,re,glob,os
src=sys.argv[1]; out=sys.argv[2]
res={}
for f in sorted(glob.glob(src+'/08_*.xlsx')):
  wb=openpyxl.load_workbook(f,read_only=True)
  for ws in wb.worksheets:
    if not ws.title.startswith('CUADRO'): continue
    rows=list(ws.iter_rows(values_only=True))
    title=next((c for r in rows[:4] for c in r if isinstance(c,str) and 'CUADRO' in c),'').replace('\n',' ')
    # headers: take rows 1..3, carry labels forward
    ncol=max(len(r) for r in rows[:6])
    hdr=['']*ncol
    for r in rows[1:4]:
      last=''
      for j in range(ncol):
        c=r[j] if j<len(r) else None
        if c not in (None,''): last=str(c).replace('\n',' ').strip(); hdr[j]=(hdr[j]+' | '+last).strip(' |')
    ents={}
    prov=None
    pending=None
    for r in rows:
      if not r: continue
      first=next((c for c in r if c not in (None,'')),None)
      if not isinstance(first,str): continue
      lab=first.strip(); up=lab.upper()
      isent=(up=='CUSCO' or up.startswith('PROVINCIA ') or up.startswith('DISTRITO '))
      if isent or pending:
        if isent: pending=lab
        lab=pending; up=lab.upper()
        r=[first]+[c for c in r[r.index(first)+1:]]
        vals=[]
        for c in r[1:]:
          if isinstance(c,(int,float)): vals.append(c)
          elif isinstance(c,str) and re.fullmatch(r'-?\d+(\.\d+)?',c.strip()): vals.append(float(c))
          elif c in (None,''): vals.append(None)
          elif isinstance(c,str) and c.strip()=='-': vals.append(0)
          else: vals.append(None)
        if not any(v for v in vals if v): continue
        pending=None
        if up.startswith('PROVINCIA '): prov=lab[10:].strip()
        key=('REGION' if up=='CUSCO' else ('P:'+lab[10:].strip() if up.startswith('PROVINCIA ') else 'D:'+prov+':'+lab[9:].strip()))
        if key not in ents: ents[key]=vals
    res[os.path.basename(f)[3:-5]+'/'+ws.title]={'title':title,'hdr':hdr[1:],'ents':ents}
json.dump(res,open(out,'w'),ensure_ascii=False)
for k,v in res.items(): print(k,'|',len(v['ents']),'|',v['title'][:150])
