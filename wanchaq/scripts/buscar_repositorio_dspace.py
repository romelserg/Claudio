import json,sys,urllib.parse,subprocess,re
base=sys.argv[1]; q=sys.argv[2]; n=sys.argv[3] if len(sys.argv)>3 else '15'
url=f"{base}/server/api/discover/search/objects?query={urllib.parse.quote(q)}&size={n}&dsoType=ITEM"
raw=subprocess.run(['curl','-sSL','-m','60','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout
d=json.loads(raw); sr=d['_embedded']['searchResult']
print('#',q,'total',sr['page']['totalElements'])
for o in sr['_embedded']['objects']:
  it=o['_embedded']['indexableObject']; md=it['metadata']
  g=lambda k:(md.get(k) or [{'value':''}])[0]['value']
  ab=re.sub(r'\s+',' ',g('dc.description.abstract'))
  print('-',g('dc.date.issued')[:4],'|',it['name'][:170],'| hdl',it['handle']); 
  if ab: print('   ',ab[:700])
