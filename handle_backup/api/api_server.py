from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import base64
import hmac
import time
from hashlib import sha256
from urllib.parse import urlparse

# 配置信息
PORT = 19328
JSON_DIR = "/data/vnstat_backup/json"
SECRET_KEY = b"secret_key"
VALID_USER = {
    "username": "username",
    "password": "password"
}

class JWTManager:
    @staticmethod
    def generate_token(username, expire_seconds=3600):
        """生成JWT Token"""
        header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        payload = json.dumps({
            "sub": username,
            "exp": int(time.time()) + expire_seconds,
            "iat": int(time.time())
        }).encode()
        
        # Base64编码
        header_b64 = base64.urlsafe_b64encode(header).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        
        # 生成签名
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(SECRET_KEY, signing_input, sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @staticmethod
    def verify_token(token):
        """验证JWT Token"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return {"valid": False, "error": "Invalid token format"}
                
            # 解码各部分
            header = json.loads(base64.urlsafe_b64decode(parts[0] + "==="))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==="))
            
            # 验证签名
            signing_input = f"{parts[0]}.{parts[1]}".encode()
            expected_sig = base64.urlsafe_b64decode(parts[2] + "===")
            actual_sig = hmac.new(SECRET_KEY, signing_input, sha256).digest()
            
            if not hmac.compare_digest(expected_sig, actual_sig):
                return {"valid": False, "error": "Invalid signature"}
                
            # 检查过期时间
            if time.time() > payload["exp"]:
                return {"valid": False, "error": "Token expired"}
                
            return {"valid": True, "payload": payload}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}

class APIHandler(BaseHTTPRequestHandler):
    def _send_response(self, status_code, data=None):
        """统一响应处理"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if data is not None:
            self.wfile.write(json.dumps(data).encode())

    def _parse_body(self):
        """解析请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(content_length)) if content_length else {}

    def do_POST(self):
        """处理登录请求"""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/auth/login':
            try:
                data = self._parse_body()
                if data.get('username') == VALID_USER['username'] and data.get('password') == VALID_USER['password']:
                    token = JWTManager.generate_token(VALID_USER['username'])
                    self._send_response(200, {"token": token, "expires_in": 3600})
                else:
                    self._send_response(401, {"error": "Invalid credentials"})
            except Exception as e:
                self._send_response(500, {"error": str(e)})
        else:
            self._send_response(404)

    def do_GET(self):
        """处理数据请求"""
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith('/backups/'):
            # 验证Token
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self._send_response(401, {"error": "Missing authorization token"})
                return
                
            token = auth_header.split(' ')[1]
            verification = JWTManager.verify_token(token)
            
            if not verification["valid"]:
                self._send_response(401, {"error": verification["error"]})
                return
                
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