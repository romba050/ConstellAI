"""One-command local API and UI. Python 3.10+, standard library only."""
import argparse
import json
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, unquote
from atlas.data import EDITION, dataset, search, discovery, sources
from atlas.api import disease_bundle
from atlas.ai import extract
from atlas.briefs import brief

class Handler(BaseHTTPRequestHandler):
    def _headers(self,status,kind,length):
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(length))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()

    def json_response(self,payload,status=200):
        data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self._headers(status,'application/json; charset=utf-8',len(data))
        self.wfile.write(data)

    def do_GET(self):
        route=urlsplit(self.path)
        q=parse_qs(route.query)
        try:
            if route.path=='/api/health':
                return self.json_response(dict(status='ok',edition='Buffalo Atlas',external_api_required=False,snapshot_date=dataset()['retrieved_at']))
            if route.path=='/api/search':
                query=q.get('q',[''])[0][:200]
                return self.json_response(search(query))
            if route.path.startswith('/api/diseases/'):
                return self.json_response(disease_bundle(unquote(route.path.removeprefix('/api/diseases/'))))
            if route.path=='/api/discovery':
                return self.json_response(discovery(q.get('id',[''])[0]))
            if route.path=='/api/sources':
                return self.json_response(dict(sources=list(sources().values())))
            if route.path=='/api/brief':
                doc=brief(q.get('id',['angelman'])[0],q.get('type',['evidence'])[0])
                if q.get('download')==['1']:
                    data=doc['text'].encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type','text/plain; charset=utf-8')
                    self.send_header('Content-Disposition','attachment; filename="'+doc['filename']+'"')
                    self.send_header('Content-Length',str(len(data)))
                    self.send_header('X-Content-Type-Options','nosniff')
                    self.end_headers();self.wfile.write(data)
                    return
                return self.json_response(doc)
            if route.path.startswith('/api/'):
                return self.json_response(dict(error='Unknown API route'),404)
            frontend=EDITION/'frontend'
            webroot=frontend/'dist' if (frontend/'dist'/'index.html').exists() else frontend
            relative='index.html' if route.path in {'/','/demo','/demo/'} else unquote(route.path).lstrip('/')
            file=(webroot/relative).resolve()
            if not file.is_relative_to(webroot.resolve()) or not file.is_file():
                return self.json_response(dict(error='File not found'),404)
            data=file.read_bytes()
            kind='text/javascript' if file.suffix=='.js' else mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            self._headers(200,kind,len(data)); self.wfile.write(data)
        except (ValueError,KeyError,IndexError):
            self.json_response(dict(error='Unknown or invalid request'),400)

    def do_POST(self):
        if self.path!='/api/ai/extract':
            return self.json_response(dict(error='Unknown API route'),404)
        # Same-origin UI requests only. No patient records are accepted or persisted.
        origin=self.headers.get('Origin')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=8192:
                raise ValueError('Invalid payload length')
            raw=self.rfile.read(length)
            # Drain the bounded request before rejecting it: unread POST bytes can
            # reset the connection on Windows instead of delivering the 403.
            if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:
                return self.json_response(dict(error='Origin rejected'),403)
            payload=json.loads(raw)
            if not isinstance(payload,dict):
                raise ValueError('Expected an object')
            graph=disease_bundle(payload.get('disease_id','angelman'))['graph']
            provider=payload.get('provider','local')
            if provider not in {'local','openai'}:
                raise ValueError('Unknown provider')
            return self.json_response(extract(payload.get('source_id',''),{n['id'] for n in graph['nodes']},payload.get('live') is True,provider))
        except (ValueError,TypeError,KeyError):
            self.json_response(dict(error='Invalid evidence extraction request'),400)

def make_server(port=8795):
    # Validate every curated graph before admitting requests.
    for d in dataset()['diseases']:
        disease_bundle(d['id'])
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8795)
    args=parser.parse_args()
    with make_server(args.port) as server:
        print(f'MEDR5 Atlas: http://127.0.0.1:{server.server_port} — cached research demo',flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
