# api_server.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

PORT = 19328
JSON_DIR = "/data/vnstat_backup/json"

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 解析请求路径
            path_parts = self.path.split('/')
            if len(path_parts) != 3 or path_parts[1] != 'vnstat':
                self.send_response(404)
                self.end_headers()
                return
                
            day = path_parts[2]
            file_path = os.path.join(JSON_DIR, f"vnstat_{day}.json")
            
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "File not found",
                    "status": 404
                }).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": str(e),
                "status": 500
            }).encode())

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', PORT), APIHandler)
    print(f"Server running on port {PORT}")
    server.serve_forever()