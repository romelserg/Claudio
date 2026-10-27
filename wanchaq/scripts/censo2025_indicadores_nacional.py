import json,sys
N=json.load(open(sys.argv[1])); N={k.replace('N° ','N°'):v for k,v in N.items()}
def pct(sheet,num,den=0):
  res={}
  for k,v in N[sheet]['ents'].items():
    n=sum((v[i] or 0) for i in (num if isinstance(num,(list,tuple)) else [num])); d=v[den] or 0
    if d: res[k]=100*n/d
  return res
def pctnot(sheet,idx,den=0): return {k:100*((v[den] or 0)-(v[idx] or 0))/v[den] for k,v in N[sheet]['ents'].items() if v[den]}
CV='Caracteristicas_de_la_vivienda/CUADRO N°'; CH='Caracteristicas_del_hogar/CUADRO N°'; ED='Educacion/CUADRO N°'; SB='Servicios_basicos_de_la_vivienda/CUADRO N°'; ES='Estado_civil_identidad_y_seguro_de_salud/CUADRO N°6'
I={
 'Viviendas desocupadas (%)':pct(CV+'1',7),'Viviendas de uso ocasional (%)':pct(CV+'1',5),
 'Viviendas de adobe o tapia (%)':pct(CV+'6',[3,4]),'Viviendas de 1 habitación (%)':pct(CV+'9',1),
 'Hogares de 1 persona (%)':pct(CH+'2',1),'Hogares que cocinan con leña (%)':pct(CH+'5',2),
 'Hogares que cocinan con bosta o estiércol (%)':pct(CH+'5',6),
 'Basura por recolector municipal (%)':pct(CH+'6',1),'Basura quemada (%)':pct(CH+'6',3),
 'Hogares con algún miembro en el extranjero (%)':pctnot(CH+'7',8),
 'Población 5+ con alguna discapacidad (%)':pctnot('Discapacidad/CUADRO N°1',8),
 'Población 3+ sin nivel educativo (%)':pct(ED+'1',1),
 'Población 3+ con superior universitaria completa o posgrado (%)':pct(ED+'1',[9,10]),
 'Población 3+ que usó internet (%)':pct(ED+'10',4),
 'Afiliados a EsSalud (%)':pct(ES,2),'Afiliados al SIS (%)':pct(ES,1),'Sin seguro de salud (%)':pct(ES,6),
 'Se identifica como quechua (%)':pct('Etnicidad/CUADRO N°1',1),
 'Mujeres 12+ sin hijos (%)':pct('Fecundidad/CUADRO N°1',9),
 'Madres que tuvieron su primer hijo antes de los 20 (%)':pct('Fecundidad/CUADRO N°5',[2,3],1),
 'Agua de red todos los días (% de viviendas con red)':pct(SB+'5',1),
 'Desagüe dentro de la vivienda (%)':pct(SB+'9',1),
 'Hogares con refrigeradora (%)':pct('Equipamiento_del_hogar/CUADRO N°1',6),
 'Hogares con internet fijo (%)':pct('Equipamiento_del_hogar/CUADRO N°2',3),
}
deps=[k for k in N[ED+'1']['ents'] if k!='PERÚ']
print(len(deps),'departamentos')
print(f"{'indicador':62} {'Cusco':>6} {'Perú':>6} {'rk/26':>5}  máx / mín")
for n,d in I.items():
  s=sorted([(d[k],k) for k in deps if k in d],reverse=True)
  rk=[k for _,k in s].index('CUSCO')+1
  print(f"{n[:62]:62} {d['CUSCO']:6.1f} {d['PERÚ']:6.1f} {rk:5}  {s[0][1][:14]} {s[0][0]:.1f} / {s[-1][1][:14]} {s[-1][0]:.1f}")
json.dump({n:{k:round(v,3) for k,v in d.items()} for n,d in I.items()},open(sys.argv[2],'w'),ensure_ascii=False)
