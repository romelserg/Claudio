import openpyxl,re,json,sys
src,out=sys.argv[1],sys.argv[2]
ws=openpyxl.load_workbook(src,read_only=True)['CUADRO N°2']
ents=[];cur=None;prov=None
for r in ws.iter_rows(values_only=True):
  c=[x for x in r if x not in (None,'')]
  if not c or not isinstance(c[0],str): continue
  lab=c[0].strip()
  up=lab.upper()
  if len(c)>=4 and (up=='CUSCO' or up.startswith('PROVINCIA ') or up.startswith('DISTRITO ')) and isinstance(c[1],(int,float,str)):
    try: tot=int(c[1])
    except: continue
    kind='region' if up=='CUSCO' else ('provincia' if up.startswith('PROVINCIA') else 'distrito')
    if kind=='provincia': prov=lab[10:].strip()
    cur={'nombre':lab.split(' ',1)[1].strip() if kind!='region' else 'Región Cusco','tipo':kind,'provincia':prov if kind!='region' else None,'total':tot,'h':int(c[2]),'m':int(c[3]),'edad':{}}
    ents.append(cur); continue
  if cur is None: continue
  m=re.match(r'^(\d+)\s+(?:y más\s+)?años?(?: y más)?$',lab) or re.match(r'^(\d+) y más años$',lab)
  if lab=='Menores de 1 año': a=0
  elif lab=='De 100 y más años': a=100
  elif m: a=int(m.group(1))
  else: continue
  if a in cur['edad']: continue
  cur['edad'][a]=[int(c[1]),int(c[2]),int(c[3])]
bad=[e['nombre'] for e in ents if abs(sum(v[0] for v in e['edad'].values())-e['total'])>0]
print(len(ents),'entidades; descuadres:',bad[:10])
json.dump(ents,open(out,'w'),ensure_ascii=False)
