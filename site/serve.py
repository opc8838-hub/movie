"""本地预览：支持视频拖动进度的静态服务器。python site/serve.py [端口]"""
import http.server, os, re, sys, webbrowser
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8799


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_GET(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        m = re.match(r'bytes=(\d+)-(\d*)', rng)
        if not m:
            return super().do_GET()
        size = os.path.getsize(path)
        a = int(m[1])
        b = min(int(m[2]) if m[2] else size - 1, size - 1)
        if a >= size:
            self.send_error(416)
            return
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
        self.send_header('Content-Length', str(b - a + 1))
        self.end_headers()
        try:
            with open(path, 'rb') as f:
                f.seek(a)
                left = b - a + 1
                while left > 0:
                    d = f.read(min(1 << 20, left))
                    if not d:
                        break
                    self.wfile.write(d)
                    left -= len(d)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print(f'http://127.0.0.1:{PORT}/')
    if '--no-open' not in sys.argv:
        webbrowser.open(f'http://127.0.0.1:{PORT}/')
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
