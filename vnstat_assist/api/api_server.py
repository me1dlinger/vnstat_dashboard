from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.parse import urlparse
import urllib.request
# 默认配置
DEFAULT_CONFIG = {
    "port": 19328,
    "json_dir": "/data/vnstat-assist/backups",
    "proxy_api": "$host:$port/vnstat/json.cgi"
}
# 读取配置
def load_config():
    try:
        with open('conf.json', 'r') as f:
            config = json.load(f)
        final_config = DEFAULT_CONFIG.copy()
        for key in config:
            if isinstance(config[key], dict) and key in final_config:
                final_config[key].update(config[key])
            else:
                final_config[key] = config[key]
        return final_config
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG
CONFIG = load_config()
PORT = CONFIG['port']
JSON_DIR = CONFIG['json_dir']
VNSTAT_PROXY_URL = CONFIG['proxy_api']

class APIHandler(BaseHTTPRequestHandler):
    def _proxy_vnstat_json(self):
        """代理请求到vnstat的json.cgi接口"""
        try:
            # 发起代理请求
            req = urllib.request.Request(VNSTAT_PROXY_URL)
            with urllib.request.urlopen(req) as response:
                data = response.read().decode('utf-8')
                json_data = json.loads(data)
                self._send_response(200, json_data)

        except urllib.error.URLError as e:
            self._send_response(502, {"error": f"Failed to proxy request: {str(e)}"})
        except json.JSONDecodeError:
            self._send_response(502, {"error": "Invalid JSON response from upstream"})
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    def _set_cors_headers(self):
        """设置CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
    def _send_response(self, status_code, data=None):
        """统一响应处理"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        if data is not None:
            self.wfile.write(json.dumps(data).encode())

    def _parse_body(self):
        """解析请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(content_length)) if content_length else {}
    def do_OPTIONS(self):
        """处理 OPTIONS 预检请求"""
        self.send_response(204)  # 直接返回 204
        self._set_cors_headers()
        self.end_headers()
    def do_GET(self):
        """处理数据请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/json.cgi':
            return self._proxy_vnstat_json()
        elif parsed_path.path.startswith('/backups/'):
            # 处理文件请求
            try:
                path_parts = parsed_path.path.split('/')
                if len(path_parts) != 3 or path_parts[1] != 'backups':
                    self._send_response(404)
                    return
                    
                day = path_parts[2]
                file_path = os.path.join(JSON_DIR, f"vnstat_{day}.json")
                if os.path.isfile(file_path):
                    with open(file_path, 'r') as f:
                        content = json.load(f)
                    self._send_response(200, content)
                else:
                    self._send_response(404, {"error": "File not found"})
                    
            except json.JSONDecodeError:
                self._send_response(500, {"error": "Invalid JSON file"})
            except Exception as e:
                self._send_response(500, {"error": str(e)})
        else:
            self._send_response(404)

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', PORT), APIHandler)
    print(f"Server started on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
    print("Server stopped")