import json,sys
E=json.load(open(sys.argv[1]))
def met(e):
  ed={int(k):v for k,v in e['edad'].items()}; T=e['total']
  s=lambda a,b,i=0: sum(ed[x][i] for x in ed if a<=x<=b)
  m={'nombre':e['nombre'],'tipo':e['tipo'],'provincia':e['provincia'],'total':T,
     'p0_14':100*s(0,14)/T,'p15_64':100*s(15,64)/T,'p65':100*s(65,200)/T,'p60':100*s(60,200)/T,
     'ie':100*s(65,200)/s(0,14),'dep':100*(s(0,14)+s(65,200))/s(15,64)}
  acc=0
  for a in sorted(ed):
    acc+=ed[a][0]
    if acc>=T/2: m['mediana']=a; break
  m['grupos5']=[[g, s(g,g+4,1), s(g,g+4,2)] for g in range(0,80,5)]+[[80,s(80,200,1),s(80,200,2)]]
  return m
M=[met(e) for e in E]
json.dump(M,open(sys.argv[2],'w'),ensure_ascii=False)
for m in M:
  if m['tipo']!='distrito' or m['provincia']=='CUSCO':
    print(f"{m['tipo'][:4]} {m['nombre'][:16]:16} {m['total']:8} 0-14 {m['p0_14']:5.1f} 65+ {m['p65']:5.1f} 60+ {m['p60']:5.1f} IE {m['ie']:6.1f} med {m['mediana']}")
d=sorted([m for m in M if m['tipo']=='distrito'],key=lambda m:-m['ie'])
print('rank IE Wanchaq', [i for i,m in enumerate(d) if m['nombre']=='WANCHAQ'], 'de', len(d))
print('top10 IE', [(m['nombre'],m['provincia'],round(m['ie']),m['total']) for m in d[:10]])
d2=sorted([m for m in M if m['tipo']=='distrito'],key=lambda m:-m['p60'])
print('rank 60+', [i for i,m in enumerate(d2) if m['nombre']=='WANCHAQ'], [(m['nombre'],round(m['p60'],1),m['total']) for m in d2[:8]])
