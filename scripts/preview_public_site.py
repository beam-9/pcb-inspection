"""Serve the built static portfolio locally with its known SPA routes."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]

class Preview(SimpleHTTPRequestHandler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ['/inspect','/journey','/model','/about'] or path.startswith('/journey/') or path.startswith('/read/'):
            self.path='/index.html'
        super().do_GET()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Preview,directory=str(ROOT/'web/public-dist')))
    print(f'Saved-evidence portfolio preview at http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
