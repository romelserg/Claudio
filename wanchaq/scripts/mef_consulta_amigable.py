import sys,re,html,urllib.request,urllib.parse,http.cookiejar
year,ap=sys.argv[1],sys.argv[2]   # ap: ActProy | Actividad | Proyecto
steps=[s.split('::') for s in sys.argv[3:]]  # "rowtext::ButtonLabel"
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders=[('User-Agent','Mozilla/5.0')]
base='https://apps5.mineco.gob.pe/transparencia/Navegador/'
url=base+f'Navegar_7.aspx?_tgt=fr&_uhc=yes&y={year}&ap={ap}'
t=op.open(url,timeout=120).read().decode('utf-8','ignore')
def parse(t):
  hidden=dict(re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"',t))
  buttons={}
  for inp in re.findall(r"<input[^>]*type=\"submit\"[^>]*>",t):
    n=re.search(r"name=\"([^\"]+)\"",inp); v=re.search(r"value=\"([^\"]+)\"",inp)
    if n and v: buttons[html.unescape(v.group(1))]=n.group(1)
  rows=[]
  for m in re.finditer(r'<tr[^>]*>(.*?)</tr>',t,re.S):
    r=m.group(1); g=re.search(r'name="grp1"[^>]*value="([^"]*)"',r)
    cells=[re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>','',c))).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)]
    cells=[c for c in cells if c]
    if g: rows.append((g.group(1),cells))
  act=re.search(r'<form[^>]*action="([^"]+)"',t).group(1)
  return hidden,buttons,rows,html.unescape(act)
for rowtxt,btn in steps:
  hidden,buttons,rows,act=parse(t)
  sel=[r for r in rows if rowtxt.lower() in ' '.join(r[1]).lower()]
  if not sel: print('NO ROW',rowtxt); [print(r) for r in rows[:60]]; sys.exit()
  bn=buttons.get(btn)
  if not bn: print('NO BTN',btn,buttons); sys.exit()
  data=dict(hidden); data['grp1']=sel[0][0]; data[bn]=btn
  t=op.open(urllib.parse.urljoin(base,act),urllib.parse.urlencode(data).encode(),timeout=180).read().decode('utf-8','ignore')
hidden,buttons,rows,act=parse(t)
for v,c in rows: print(' | '.join(c))
