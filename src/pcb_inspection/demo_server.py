"""Loopback-only research demo. Uploads are decoded in memory and never persisted."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import mimetypes
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps
from .guard import digest
from .model_v1 import FrozenInspector, UnsupportedImage, MAX_UPLOAD_BYTES, png_url


class DemoApplication:
    def __init__(self, root):
        self.root=Path(root).resolve();self.inspector=FrozenInspector(self.root)
        self.journey=json.loads((self.root/'content/journey.json').read_text())
        self.examples=json.loads((self.root/'content/examples.json').read_text())
        self.purpose=json.loads((self.root/'content/purpose.json').read_text())
        self.evidence_index=json.loads((self.root/'content/evidence_index.json').read_text())
        smoke=json.loads((self.root/'tests/model_v1_smoke_manifest.json').read_text())
        self.cases={case['id']:case for case in smoke['cases']}
        self.busy=threading.Lock()
        self.evidence={}
        for stage in self.journey['stages']:
            for source in stage['sources']+stage['figures']:
                source_path=self.root/source['path']
                if source['path']=='README.md':source_path=self.root/'artifacts/productization/history_navigation/README.md'
                if digest(source_path)!=source['sha256']:raise ValueError('Journey source changed: '+source['path'])
                self.evidence[source['path']]=source_path
            for metric in stage['metrics']:
                source=metric['source'];self.evidence[source['path']]=self.root/source['path']
        self.evidence.update({str(p.relative_to(self.root)):p for p in (self.root/'artifacts/model_v1').iterdir() if p.is_file()})
        for source in self.purpose['sources']:
            self.evidence[source['path']]=self.root/source['path']

        preserved={x['path']:x['preserved_at'] for x in json.loads((self.root/'artifacts/productization/historical_preservation.json').read_text())['checks']}
        for source in self.evidence_index['files']:
            path=self.root/preserved.get(source['path'],source['path'])
            if digest(path)!=source['sha256']:raise ValueError('Reader source changed: '+source['path'])
            self.evidence[source['path']]=path

    def inspect_bytes(self,data):
        if not self.busy.acquire(blocking=False):
            raise BlockingIOError('An inspection is already running. Try again when it finishes.')
        try:return self.inspector.inspect(data)
        finally:self.busy.release()

    def inspect_example(self,identity):
        if identity not in self.cases:raise ValueError('Choose an available benchmark example.')
        case=self.cases[identity];path=self.root/case['image_path']
        if digest(path)!=case['image_sha256']:raise ValueError('Benchmark image identity changed.')
        result=self.inspect_bytes(path.read_bytes());payload=result.payload()
        payload['benchmark']={'id':identity,'image_id':case['image_id'],'annotation_available':bool(case['mask_path']),
                              'known_outcome':'known missed anomaly' if identity=='known_small_missing_miss' else 'benchmark example'}
        if case['mask_path']:
            if digest(self.root/case['mask_path'])!=case['mask_sha256']:raise ValueError('Benchmark annotation identity changed.')
            with Image.open(self.root/case['mask_path']) as mask:
                gt=ImageOps.exif_transpose(mask).convert('L').resize(tuple(payload['display_size']),Image.Resampling.NEAREST)
                payload['ground_truth']=png_url(gt.point(lambda value:255 if value>0 else 0))
        return payload


class Handler(BaseHTTPRequestHandler):
    server_version='PCB-AD-local/1.0'

    def __init__(self,*args,application,**kwargs):
        self.application=application
        super().__init__(*args,**kwargs)

    def valid_host(self):
        # Reject cross-site requests to the loopback inference service.
        host=self.headers.get('Host','').split(':')[0]
        return host in ['127.0.0.1','localhost']

    def send(self,status,body,content_type='application/json; charset=utf-8'):
        if isinstance(body,(dict,list)):body=json.dumps(body,allow_nan=False).encode()
        elif isinstance(body,str):body=body.encode()
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host():self.send(403,{'error':'Use the local demo address.'});return
        path=unquote(urlsplit(self.path).path)
        if path=='/model-info':self.send(200,self.application.inspector.metadata);return
        if path=='/api/journey':self.send(200,self.application.journey);return
        if path=='/api/examples':self.send(200,self.application.examples);return
        if path=='/api/evidence-index':self.send(200,self.application.evidence_index);return
        if path=='/api/purpose':self.send(200,self.application.purpose);return
        if path=='/health':self.send(200,{'status':'ready','model':self.application.inspector.metadata['name']});return
        if path.startswith('/evidence/'):
            source=path.removeprefix('/evidence/');p=self.application.evidence.get(source)
            if p is None:self.send(404,{'error':'Evidence not available.'});return
        elif path.startswith('/assets/'):
            assets=(self.application.root/'web/assets').resolve();p=(assets/path.removeprefix('/assets/')).resolve()
            if p.parent!=assets or not p.is_file():self.send(404,{'error':'Asset not available.'});return
        elif path.startswith('/fonts/'):
            folder=(self.application.root/'web/dist/fonts').resolve();p=(folder/path.removeprefix('/fonts/')).resolve()
            if p.parent!=folder or not p.is_file():self.send(404,{'error':'Font not available.'});return
        elif path in ['/app.js','/app.css']:
            p=self.application.root/'web/dist'/path[1:]
        elif path.startswith('/read/') or path in ['/','/inspect','/journey','/model','/about'] or (path.startswith('/journey/') and path.split('/')[-1] in {s['id'] for s in self.application.journey['stages']}):
            p=self.application.root/'web/dist/index.html'
        else:self.send(404,{'error':'Page not found.'});return
        if not p.is_file():self.send(503,{'error':'Build the frontend with npm ci and npm run build in web/.'});return
        content_type=mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
        if p.suffix in ['.md','.csv']:content_type='text/plain; charset=utf-8'
        self.send(200,p.read_bytes(),content_type)

    def do_POST(self):
        if not self.valid_host():self.send(403,{'error':'Use the local demo address.'});return
        origin=self.headers.get('Origin')
        if origin and origin not in ['http://'+self.headers['Host']]:self.send(403,{'error':'Use the local demo page to inspect an image.'});return
        path=urlsplit(self.path).path
        if path not in ['/api/inspect','/api/inspect-example']:self.send(404,{'error':'Endpoint not found.'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_UPLOAD_BYTES:self.send(413,{'error':'Choose an image smaller than 12 MiB.'});return
            self.connection.settimeout(30);data=self.rfile.read(length)
            if len(data)!=length:raise ValueError('Upload was interrupted. Please retry.')
            if path=='/api/inspect-example':
                body=json.loads(data);payload=self.application.inspect_example(body.get('id',''))
            else:payload=self.application.inspect_bytes(data).payload()
            self.send(200,payload)
        except BlockingIOError as exc:self.send(503,{'error':str(exc)})
        except (UnsupportedImage,ValueError,TypeError,AttributeError) as exc:self.send(400,{'error':str(exc)})
        except (TimeoutError,OSError):self.send(400,{'error':'The upload could not be read. Please retry.'})
        except Exception:
            self.send(500,{'error':'Inspection could not finish. Check the local server and try again.'})
            import traceback;traceback.print_exc()

    def log_message(self,fmt,*args):
        # Standard route/status logs contain no upload bytes, filenames or image metadata.
        super().log_message(fmt,*args)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args();application=DemoApplication(args.root)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,application=application))
    print(f'PCB-AD-v1.0 ready at http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
