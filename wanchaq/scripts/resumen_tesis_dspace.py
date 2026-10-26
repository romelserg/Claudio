import json,sys,urllib.parse,subprocess,re
base=sys.argv[1]
for h in sys.argv[2:]:
  url=f"{base}/server/api/discover/search/objects?query={urllib.parse.quote('handle:'+h)}&size=1&dsoType=ITEM"
  raw=subprocess.run(['curl','-sSL','-m','60','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout
  try:
    o=json.loads(raw)['_embedded']['searchResult']['_embedded']['objects'][0]
  except Exception as e:
    print('ERR',h,e); continue
  it=o['_embedded']['indexableObject']; md=it['metadata']
  g=lambda k:'; '.join(x['value'] for x in (md.get(k) or []))
  print('=====',h,'|',it['name']); print('Autor:',g('dc.contributor.author')[:150],'| Año:',g('dc.date.issued')[:4],'| uuid',it['uuid'])
  print(re.sub(r'\s+',' ',g('dc.description.abstract'))[:3000]); print()
