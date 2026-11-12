import sys,json,faulthandler,threading,re
faulthandler.enable()
sys.setrecursionlimit(100000)
import convertir as C
if __name__=='__main__':
    K=[x for x in json.loads((C.H/'canciones.json').read_text(encoding='utf8')) if x['keep'] and re.search(sys.argv[1],x['folder'])]
    r=C.one(K[0]);print('RESULT',len(r['charts']),str(r['errors'])[:600])
