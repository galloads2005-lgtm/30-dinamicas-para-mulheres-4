import http.server
import socketserver
import os
import threading

PORT = 5000

CACHE_EXTENSIONS = {'.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.mp4', '.mp3'}
CACHE_MAX_AGE = 86400  # 1 dia para assets estáticos

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.translate_path(self.path)
        ext = os.path.splitext(path)[1].lower()

        if ext in CACHE_EXTENSIONS:
            self.send_header('Cache-Control', f'public, max-age={CACHE_MAX_AGE}')
        else:
            self.send_header('Cache-Control', 'no-cache, must-revalidate')

        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)

        if os.path.isdir(path) or not os.path.isfile(path):
            super().do_GET()
            return

        range_header = self.headers.get('Range')
        if not range_header:
            super().do_GET()
            return

        file_size = os.path.getsize(path)
        byte_range = range_header.strip().replace('bytes=', '')
        parts = byte_range.split('-')
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
        self.send_header('Content-Length', str(length))
        self.end_headers()

        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk_size = min(524288, remaining)
                data = f.read(chunk_size)
                if not data:
                    break
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(data)

    def log_message(self, format, *args):
        super().log_message(format, *args)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


with ThreadedTCPServer(("0.0.0.0", PORT), RangeRequestHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()
