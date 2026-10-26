import sys,re,unicodedata
M,POB,MEF=sys.argv[1:4]
def norm(s): return re.sub(r'\s+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().upper()).strip()
pop={}
for l in open(POB,encoding='utf-8',errors='ignore'):
  m=re.match(r'^\s*(\d{6})\s+(.+?)\s+(\d{1,3}(?: \d{3})*)\s+(\d+,\d)\s+(\d+,\d)\s+\d+\s+\d[\d ]*$',l)
  if m and m.group(1) not in pop: pop[m.group(1)]=(norm(m.group(2)),int(m.group(3).replace(' ','')))
pop['040129']=('AREQUIPA AREQUIPA JOSE LUIS BUSTAMANTE Y RIVERO',82642)
def findpop(dep,dist):
  for u,(txt,n) in pop.items():
    if txt==dep+' '+dep+' '+dist: return n
def load(f):
  d={}
  for l in open(f):
    p=[x.strip() for x in l.split('|')]
    if len(p)<9: continue
    d[norm(p[0].split(': ',1)[-1])]=(int(p[2].replace(',','')),int(p[6].replace(',','')))
  return d
sel=sys.argv[4].split(',')
rows=[]
for reg,dep,ft,fp in [('Lima','LIMA',f'{M}/lima_2025_ActProy.txt',f'{M}/lima_2025_Proyecto.txt'),('Arequipa','AREQUIPA',f'{M}/aqp_2025_ActProy.txt',f'{M}/aqp_2025_Proyecto.txt'),('Cusco','CUSCO',f'{MEF}/prov_2025_ActProy.txt',f'{MEF}/prov_2025_Proyecto.txt')]:
  T,P=load(ft),load(fp)
  for k,t in T.items():
    if 'PROVINCIAL' in k: continue
    dist=k.replace('MUNICIPALIDAD DISTRITAL DE ','').strip()
    if dist not in sel: continue
    n=findpop(dep,dist)
    p=P.get(k,(0,0))
    rows.append((reg,dist,n,t[0],p[0],p[1]))
print(f"{'distrito':34} {'pob2020':>8} {'PIM/hab':>8} {'%inv':>6} {'invPIM/hab':>10} {'invDev/hab':>10}")
for r in sorted(rows,key=lambda r:-(r[5]/r[2] if r[2] else 0)):
  if not r[2]: print('SIN POB',r); continue
  print(f"{r[0]+' '+r[1]:34} {r[2]:8,} {r[3]/r[2]:8,.0f} {100*r[4]/r[3]:5.1f}% {r[4]/r[2]:10,.0f} {r[5]/r[2]:10,.0f}")
