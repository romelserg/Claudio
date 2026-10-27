import json,glob,sys,csv,os
S=sys.argv[1]; outcsv=sys.argv[2]
D={};P={}
for f in glob.glob(S+'/pais/out/*.json'):
  j=json.load(open(f)); D.update(j['ind']); P.update(j['pop'])
N=json.load(open(S+'/viz/nac_ind.json')); Rg=json.load(open(S+'/viz/indic25.json'))
W=[k for k in D if k.startswith('08|CUSCO|WANCHAQ')][0]
UP=['Población 3+ con superior universitaria completa o posgrado (%)','Población 3+ con posgrado (%)','Población 3+ que usó internet (%)','Población 3+ que usó computadora o laptop (%)','Afiliados a EsSalud (%)','Con seguro privado (%)','Basura por recolector municipal (%)','Agua de red todos los días (% de viviendas con red)','Desagüe dentro de la vivienda (%)','Hogares con refrigeradora (%)','Hogares con lavadora (%)','Hogares con microondas (%)','Hogares con internet fijo (%)']
DOWN=['Población 3+ sin nivel educativo (%)','Sin seguro de salud (%)','Hogares que cocinan con leña (%)','Viviendas de adobe o tapia (%)','Viviendas de 1 habitación (%)','Madres que tuvieron su primer hijo antes de los 20 (%)','Viviendas desocupadas (%)','Población 5+ con alguna discapacidad (%)']
inds=list(D[W].keys())
def rank(keys,n,direction):
  vals=[(D[k][n],k) for k in keys if n in D[k]]
  vals.sort(key=lambda x:x[0], reverse=(direction!='down'))
  # puesto con empates: 1 + cuántos estrictamente mejores
  w=D[W][n]
  better=sum(1 for v,_ in vals if (v>w if direction!='down' else v<w))
  return better+1,len(vals)
rows=[]
for n in inds:
  dr='down' if n in DOWN else ('up' if n in UP else 'neutral')
  kp=[k for k in D if k.startswith('08|CUSCO|')]; kr=[k for k in D if k.startswith('08|')]; kn=list(D)
  rp,np_=rank(kp,n,dr); rr,nr=rank(kr,n,dr); rn,nn=rank(kn,n,dr)
  big=[k for k in kn if P.get(k,0)>=50000]; rb,nb=rank(big,n,dr) if W in big else (None,None)
  rows.append([n,dr,round(D[W][n],1),rp,np_,rr,nr,rn,nn,rb,nb])
  print(f"{n[:58]:58} {dr:7} {D[W][n]:6.1f}  prov {rp}/{np_}  reg {rr}/{nr}  país {rn}/{nn}  ≥50k {rb}/{nb}")
with open(outcsv,'w',newline='') as f:
  w=csv.writer(f); w.writerow(['indicador','sentido','wanchaq','puesto_provincia','de_provincia','puesto_region','de_region','puesto_pais','de_pais','puesto_distritos_50mil_mas','de_distritos_50mil_mas']); w.writerows(rows)
print('distritos país:',len(D),' con ≥50k:',sum(1 for k in D if P.get(k,0)>=50000))
