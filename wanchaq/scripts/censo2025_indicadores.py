import json,sys,csv
R=json.load(open(sys.argv[1])); out=sys.argv[2]
def g(sheet): return R[sheet]['ents']
def pct(sheet,num,den=0):
  E=g(sheet); res={}
  for k,v in E.items():
    n=sum((v[i] or 0) for i in (num if isinstance(num,(list,tuple)) else [num]))
    d=v[den] or 0
    if d: res[k]=100*n/d
  return res
def pctnot(sheet,idx,den=0):
  E=g(sheet); return {k:100*((v[den] or 0)-(v[idx] or 0))/v[den] for k,v in E.items() if v[den]}
CV='Caracteristicas_de_la_vivienda/CUADRO N°'; CH='Caracteristicas_del_hogar/CUADRO N°'; ED='Educacion/CUADRO N°'; SB='Servicios_basicos_de_la_vivienda/CUADRO N°'
I={
 'Viviendas desocupadas (%)':pct(CV+'1',7),
 'Viviendas de uso ocasional (%)':pct(CV+'1',5),
 'Viviendas de adobe o tapia (%)':pct(CV+'6',[3,4]),
 'Viviendas de 1 habitación (%)':pct(CV+'9',1),
 'Hogares de 1 persona (%)':pct(CH+'2',1),
 'Hogares de 1 o 2 personas (%)':pct(CH+'2',[1,2]),
 'Hogares que cocinan con leña (%)':pct(CH+'5',2),
 'Hogares que no cocinan (%)':pct(CH+'5',7),
 'Basura por recolector municipal (%)':pct(CH+'6',1),
 'Hogares con algún miembro en el extranjero (%)':pctnot(CH+'7',7),
 'Población 5+ con alguna discapacidad (%)':pctnot('Discapacidad/CUADRO N°1',8),
 'Población 3+ sin nivel educativo (%)':pct(ED+'1',1),
 'Población 3+ con superior universitaria completa o posgrado (%)':pct(ED+'1',[9,10]),
 'Población 3+ con posgrado (%)':pct(ED+'1',10),
 'Población 3+ que usó internet (%)':pct(ED+'10',4),
 'Población 3+ que usó computadora o laptop (%)':pct(ED+'10',1),
 'Afiliados a EsSalud (%)':pct('Estado_civil_identidad_y_seguro_de_salud/CUADRO N°6',2),
 'Afiliados al SIS (%)':pct('Estado_civil_identidad_y_seguro_de_salud/CUADRO N°6',1),
 'Con seguro privado (%)':pct('Estado_civil_identidad_y_seguro_de_salud/CUADRO N°6',4),
 'Sin seguro de salud (%)':pct('Estado_civil_identidad_y_seguro_de_salud/CUADRO N°6',6),
 'Se identifica como quechua (%)':pct('Etnicidad/CUADRO N°1',1),
 'Se identifica como mestizo (%)':pct('Etnicidad/CUADRO N°1',9),
 'Se identifica como blanco (%)':pct('Etnicidad/CUADRO N°1',8),
 'Hogares con jefatura de 60+ años (%)':pct('Indicadores_demograficos/CUADRO N°6',5),
 'Mujeres 12+ sin hijos (%)':pct('Fecundidad/CUADRO N°1',9),
 'Madres que tuvieron su primer hijo antes de los 20 (%)':pct('Fecundidad/CUADRO N°5',[2,3],1),
 'Madres que tuvieron su primer hijo a los 30 o más (%)':pct('Fecundidad/CUADRO N°5',[6,7,8,9,10],1),
 'Agua de red todos los días (% de viviendas con red)':pct(SB+'5',1),
 'Desagüe dentro de la vivienda (%)':pct(SB+'9',1),
 'Hogares con refrigeradora (%)':pct('Equipamiento_del_hogar/CUADRO N°1',6),
 'Hogares con lavadora (%)':pct('Equipamiento_del_hogar/CUADRO N°1',7),
 'Hogares con microondas (%)':pct('Equipamiento_del_hogar/CUADRO N°1',5),
 'Hogares con auto o camioneta (%)':pct('Equipamiento_del_hogar/CUADRO N°2',6),
 'Hogares con internet fijo (%)':pct('Equipamiento_del_hogar/CUADRO N°2',3),
}
keys=list(g('Indicadores_demograficos/CUADRO N°1').keys())
dist=[k for k in keys if k.startswith('D:')]; provs=[k for k in keys if k.startswith('P:')]
W='D:CUSCO:WANCHAQ'
rows=[]
print(f"{'indicador':62} {'Wánchaq':>8} {'rk/116':>6} {'rkProv/8':>8} {'Prov':>7} {'Región':>7}  max distrito")
for name,d in I.items():
  dv=sorted([(d[k],k) for k in dist if k in d],reverse=True)
  rk=[k for _,k in dv].index(W)+1
  pv=sorted([(d[k],k) for k in dist if k in d and k.startswith('D:CUSCO:')],reverse=True)
  rkp=[k for _,k in pv].index(W)+1
  top=dv[0]
  print(f"{name[:62]:62} {d[W]:8.1f} {rk:6} {rkp:8} {d['P:CUSCO']:7.1f} {d['REGION']:7.1f}  {top[1][2:]} {top[0]:.1f}")
  rows.append(name)
json.dump({n:{k:round(v,3) for k,v in d.items()} for n,d in I.items()},open(out,'w'),ensure_ascii=False)
