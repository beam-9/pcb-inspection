"""Index reader sources and linked historical evidence without changing originals."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit
import posixpath
ROOT=Path(__file__).resolve().parents[1]
def main():
    history=json.loads((ROOT/'artifacts/productization/historical_preservation.json').read_text())
    preserved={c['path']:c['preserved_at'] for c in history['checks']}
    journey=json.loads((ROOT/'content/journey.json').read_text())
    purpose=json.loads((ROOT/'content/purpose.json').read_text())
    seeds={x['path'] for s in journey['stages'] for x in s['sources']+s['figures']+[m['source'] for m in s['metrics']]}
    seeds.update(x['path'] for x in purpose['sources'])
    seeds.update(str(p.relative_to(ROOT)) for p in (ROOT/'artifacts/model_v1').iterdir() if p.is_file())
    allowed={'.md','.csv','.json','.lock','.txt','.png','.jpg','.jpeg','.webp'}
    pending=list(seeds);found={}
    while pending:
        path=pending.pop()
        if path in found:continue
        if path not in seeds and path not in preserved:continue
        if Path(path).suffix.lower() not in allowed:continue
        actual=ROOT/preserved.get(path,path)
        if not actual.is_file():continue
        found[path]={'path':path,'sha256':hashlib.sha256(actual.read_bytes()).hexdigest()}
        if actual.suffix=='.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)',actual.read_text()):
                u=urlsplit(target)
                if u.scheme or u.netloc or not u.path:continue
                relative=posixpath.normpath(posixpath.join(posixpath.dirname(path),unquote(u.path)))
                if not relative.startswith('../') and not relative.startswith('/') and relative not in found:pending.append(relative)
    output=ROOT/'content/evidence_index.json'
    output.write_text(json.dumps({'files':[found[p] for p in sorted(found)]},indent=2)+'\n')
    print(f'Indexed {len(found)} original sources and linked figures.')
if __name__=='__main__':main()
