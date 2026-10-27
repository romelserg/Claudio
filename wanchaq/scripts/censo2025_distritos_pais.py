import openpyxl,sys,json,re,os,subprocess,shutil
code=sys.argv[1]; work=sys.argv[2]; outdir=sys.argv[3]
B='https://proyectos.inei.gob.pe/dir-segmentacion-ci/postcensal/prod/adjuntos/censos-2025/descarga_datos/tabulados/'+code
FILES={'Caracteristicas_de_la_vivienda':'vivienda','Servicios_basicos_de_la_vivienda':'vivienda','Caracteristicas_del_hogar':'hogar','Equipamiento_del_hogar':'hogar','Educacion':'poblacion','Discapacidad':'poblacion','Etnicidad':'poblacion','Estado_civil_identidad_y_seguro_de_salud':'poblacion','Fecundidad':'poblacion','Indicadores_demograficos':'poblacion'}
# indicador: (archivo, cuadro, numerador[labels], denominador label or None=col0)
IND={
 'Viviendas desocupadas (%)':('Caracteristicas_de_la_vivienda',1,['|Desocupada | Total'],None),
 'Viviendas de uso ocasional (%)':('Caracteristicas_de_la_vivienda',1,['De uso ocasional o transitoria'],None),
 'Viviendas de adobe o tapia (%)':('Caracteristicas_de_la_vivienda',6,['Adobe','Tapia'],None),
 'Viviendas de 1 habitación (%)':('Caracteristicas_de_la_vivienda',9,['1'],None),
 'Hogares de 1 persona (%)':('Caracteristicas_del_hogar',2,['1'],None),
 'Hogares de 1 o 2 personas (%)':('Caracteristicas_del_hogar',2,['1','2'],None),
 'Hogares que cocinan con leña (%)':('Caracteristicas_del_hogar',5,['Leña'],None),
 'Basura por recolector municipal (%)':('Caracteristicas_del_hogar',6,['Por recolector municipal'],None),
 'Hogares con algún miembro en el extranjero (%)':('Caracteristicas_del_hogar',7,['!NINGUNA'],None),
 'Población 5+ con alguna discapacidad (%)':('Discapacidad',1,['!Ninguna'],None),
 'Población 3+ sin nivel educativo (%)':('Educacion',1,['Sin nivel'],None),
 'Población 3+ con superior universitaria completa o posgrado (%)':('Educacion',1,['Sup. univ. completa','^Maestría'],None),
 'Población 3+ con posgrado (%)':('Educacion',1,['^Maestría'],None),
 'Población 3+ que usó internet (%)':('Educacion',10,['Internet'],None),
 'Población 3+ que usó computadora o laptop (%)':('Educacion',10,['Computadora o Laptop'],None),
 'Afiliados a EsSalud (%)':('Estado_civil_identidad_y_seguro_de_salud',6,['EsSalud'],None),
 'Afiliados al SIS (%)':('Estado_civil_identidad_y_seguro_de_salud',6,['Seguro Integral de Salud (SIS)'],None),
 'Con seguro privado (%)':('Estado_civil_identidad_y_seguro_de_salud',6,['Seguro privado de salud'],None),
 'Sin seguro de salud (%)':('Estado_civil_identidad_y_seguro_de_salud',6,['Ninguno'],None),
 'Se identifica como quechua (%)':('Etnicidad',1,['^Quechua'],None),
 'Se identifica como mestizo (%)':('Etnicidad',1,['Mestizo'],None),
 'Se identifica como blanco (%)':('Etnicidad',1,['Blanco'],None),
 'Hogares con jefatura de 60+ años (%)':('Indicadores_demograficos',6,['^De 60'],None),
 'Población de 60 años y más (%)':('Indicadores_demograficos',3,['^De 60'],None),
 'Mujeres 12+ sin hijos (%)':('Fecundidad',1,['Ninguno'],None),
 'Madres que tuvieron su primer hijo antes de los 20 (%)':('Fecundidad',5,['Hasta 14 años','De 15 a 19 años'],'TOTAL1'),
 'Madres que tuvieron su primer hijo a los 30 o más (%)':('Fecundidad',5,['De 30 a 34 años','De 35 a 39 años','De 40 a 44 años','De 45 a 49 años','De 50 y más años'],'TOTAL1'),
 'Agua de red todos los días (% de viviendas con red)':('Servicios_basicos_de_la_vivienda',5,['Sí'],None),
 'Desagüe dentro de la vivienda (%)':('Servicios_basicos_de_la_vivienda',9,['^Red pública de desagüe dentro de la vivienda'],None),
 'Hogares con refrigeradora (%)':('Equipamiento_del_hogar',1,['^Refrige'],None),
 'Hogares con lavadora (%)':('Equipamiento_del_hogar',1,['Lavadora de ropa'],None),
 'Hogares con microondas (%)':('Equipamiento_del_hogar',1,['Horno micro-ondas'],None),
 'Hogares con auto o camioneta (%)':('Equipamiento_del_hogar',2,['Auto / camioneta'],None),
 'Hogares con internet fijo (%)':('Equipamiento_del_hogar',2,['^Conexión a internet fijo'],None),
 'Hogares en vivienda alquilada (%)':('Caracteristicas_del_hogar',3,['Alquilada'],None),
 'Hogares en vivienda propia (%)':('Caracteristicas_del_hogar',3,['^Propia, sin título','^Propia, con título'],None),
 'Hogares en vivienda propia con título (%)':('Caracteristicas_del_hogar',3,['^Propia, con título'],None),
 'Hogares en vivienda propia sin título (%)':('Caracteristicas_del_hogar',3,['^Propia, sin título'],None),
}
ONLY=sys.argv[4].split(',') if len(sys.argv)>4 else None
if ONLY:
  FILES={k:v for k,v in FILES.items() if k in ONLY}
  IND={n:v for n,v in IND.items() if v[0] in ONLY and (len(sys.argv)<6 or n in sys.argv[5].split(';'))}
os.makedirs(work,exist_ok=True)
def norm(s): return re.sub(r'\s+',' ',s).strip()
def colidx(hdr,label):
  segs=[[norm(x) for x in h.split('|')] for h in hdr]
  if label.startswith('|'):
    t=norm(label[1:]); return [i for i,h in enumerate(hdr) if norm(h.replace(' | ','|').replace('|',' | ')).endswith(t)]
  if label.startswith('^'):
    t=norm(label[1:]); return [i for i,s in enumerate(segs) if s and s[-1].startswith(t)]
  t=norm(label); return [i for i,s in enumerate(segs) if s and s[-1]==t]
res={}  # key -> {ind: val}
pop={}
for fname,sub in FILES.items():
  p=f'{work}/{code}_{fname}.xlsx'
  r=subprocess.run(['curl','-sSL','-m','900','-A','Mozilla/5.0','-o',p,f'{B}/{sub}/{fname}.xlsx'])
  if r.returncode!=0 or not os.path.exists(p): print('FAIL',code,fname,file=sys.stderr); continue
  try: wb=openpyxl.load_workbook(p,read_only=True)
  except Exception as e: print('BADXLSX',code,fname,e,file=sys.stderr); continue
  need={n:v for n,v in IND.items() if v[0]==fname}
  cuadros=sorted(set(v[1] for v in need.values()))
  if fname=='Indicadores_demograficos': cuadros=sorted(set(cuadros+[1]))
  for cn in cuadros:
    ws=next((w for w in wb.worksheets if re.fullmatch(rf'(CUADRO\s*N\s*[°ºo]?|EDUC)\s*{cn}',w.title.strip(),re.I)),None)
    if ws is None: print('NOSHEET',code,fname,cn,file=sys.stderr); continue
    rows=list(ws.iter_rows(values_only=True))
    ncol=max(len(x) for x in rows[:6]); hdr=['']*ncol
    for rr in rows[1:4]:
      for j in range(ncol):
        c=rr[j] if j<len(rr) else None
        if c not in (None,''): hdr[j]=(hdr[j]+' | '+norm(str(c))).strip(' |')
    hdr=hdr[1:]
    ents={}; pending=None; prov=None
    for rr in rows:
      if not rr: continue
      first=next((c for c in rr if c not in (None,'')),None)
      if not isinstance(first,str): continue
      lab=norm(first); up=lab.upper()
      isent=up.startswith('PROVINCIA ') or up.startswith('DISTRITO ')
      if isent and up.startswith('PROVINCIA '): prov=lab[10:]
      if isent: pending=(prov,lab[9:] if up.startswith('DISTRITO ') else None)
      if pending is None: continue
      vals=[]
      for c in rr[rr.index(first)+1:]:
        if isinstance(c,(int,float)): vals.append(c)
        elif isinstance(c,str) and re.fullmatch(r'-?\d+(\.\d+)?',c.strip()): vals.append(float(c))
        elif isinstance(c,str) and c.strip()=='-': vals.append(0)
        else: vals.append(None)
      if not any(v for v in vals if v): continue
      if pending[1] is not None:
        k=f'{code}|{pending[0]}|{pending[1]}'
        if k not in ents: ents[k]=vals
      pending=None
    if fname=='Indicadores_demograficos' and cn==1:
      for k,v in ents.items(): pop[k]=v[3] if len(v)>3 and v[3] else v[0]
    for n,(f_,c_,nums,den) in need.items():
      if c_!=cn: continue
      idx=[]; neg=None
      for l in nums:
        if l.startswith('!'): neg=colidx(hdr,l[1:])
        else: idx+=colidx(hdr,l)
      if (not idx and neg is None) or (neg is not None and not neg): print('NOCOL',code,n,file=sys.stderr); continue
      di=0
      if den=='TOTAL1':
        cand=[i for i,h in enumerate(hdr) if i>0 and norm(h.split('|')[-1])=='Total']; di=cand[0] if cand else 0
      for k,v in ents.items():
        d=v[di] or 0
        if not d: continue
        num=(d-(v[neg[0]] or 0)) if neg is not None else sum((v[i] or 0) for i in idx)
        res.setdefault(k,{})[n]=100*num/d
  os.remove(p)
of=f'{outdir}/{code}.json'
if os.path.exists(of):
  old=json.load(open(of))
  for k,v in res.items(): old['ind'].setdefault(k,{}).update(v)
  old['pop'].update(pop); pop,res=old['pop'],old['ind']
json.dump({'pop':pop,'ind':res},open(of,'w'),ensure_ascii=False)
print(code,'distritos',len(res),'pob',len(pop))
