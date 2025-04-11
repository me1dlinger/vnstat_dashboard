from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import base64
import hmac
import time
from hashlib import sha256
from urllib.parse import urlparse
import urllib.request
# 默认配置
DEFAULT_CONFIG = {
    "secret_key": "secret_key",
    "auth_enable": 1,
    "expire_seconds": 3600,
    "user": {
        "username": "username",
        "password": "password"
    },
}

def load_config_from_env():
    """从环境变量加载配置，缺失时回退到默认值"""
    config = DEFAULT_CONFIG.copy()  # 初始化为默认配置
    # 覆盖环境变量中的配置
    if "VNA_SECRET_KEY" in os.environ:
        config["secret_key"] = os.environ["VNA_SECRET_KEY"]
    if "VNA_EXPIRE_SECONDS" in os.environ:
        config["expire_seconds"] = int(os.environ["VNA_EXPIRE_SECONDS"])
    if "VNA_USERNAME" in os.environ:
        config["user"]["username"] = os.environ["VNA_USERNAME"]
    if "VNA_PASSWORD" in os.environ:
        config["user"]["password"] = os.environ["VNA_PASSWORD"]
    if "VNSTAT_API_URL" in os.environ:
        config["vnstat_api"] = os.environ["VNSTAT_API_URL"]
    config["auth_enable"] = int(os.getenv("VNA_AUTH_ENABLE", str(DEFAULT_CONFIG["auth_enable"])))

    # 仅在启用认证时验证必要字段
    if config["auth_enable"] == 1:
        required_keys = ["secret_key", "user.username", "user.password"]
        for key in required_keys:
            parts = key.split('.')
            value = config
            for part in parts:
                value = value.get(part)
                if not value:
                    raise ValueError(f"环境变量 {key} 必须配置（当启用认证时）")
    
    # 检查 vnstat_api 是否有效
    if not config["vnstat_api"].startswith(("http://", "https://")):
        raise ValueError("VNSTAT_API_URL 必须包含协议（如 http:// 或 https://）")
    return config

PORT = 19328
JSON_DIR = "/app/backups/json"

CONFIG = load_config_from_env()
SECRET_KEY = CONFIG['secret_key'].encode()  # Convert to bytes for HMAC
VALID_USER = CONFIG['user']
VNSTAT_PROXY_URL = CONFIG['vnstat_api']
EXPIRE_SECONDS = CONFIG['expire_seconds']
AUTH_ENABLED = CONFIG['auth_enable']

class JWTManager:
    @staticmethod
    def generate_token(username):
        """生成JWT Token"""
        header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        payload = json.dumps({
            "sub": username,
            "exp": int(time.time()) + EXPIRE_SECONDS,
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
    def handle_verify(self):
        """验证Token有效性"""
        if not AUTH_ENABLED:
            # 直接返回验证通过
            self._send_response(200, {"valid": True, "user": "anonymous"})
            return
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            self._send_response(401, {"valid": False, "error": "Missing token"})
            return
        token = auth_header.split(' ')[1]
        verification = JWTManager.verify_token(token)
        
        if verification["valid"]:
            self._send_response(200, {"valid": True, "user": verification["payload"]["sub"]})
        else:
            self._send_response(401, verification)
    def _proxy_vnstat_json(self):
        """代理请求到vnstat的json.cgi接口"""
        try:
            if AUTH_ENABLED:
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
    def do_POST(self):
        """处理登录请求"""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/auth/login':
            try:
                if not AUTH_ENABLED:
                    # 直接生成 Token 无需验证用户
                    token = JWTManager.generate_token(VALID_USER['username'])
                    self._send_response(200, {"token": token, "expires_in": EXPIRE_SECONDS})
                    return
                data = self._parse_body()
                if data.get('username') == VALID_USER['username'] and data.get('password') == VALID_USER['password']:
                    token = JWTManager.generate_token(VALID_USER['username'])
                    self._send_response(200, {"token": token, "expires_in": EXPIRE_SECONDS})
                else:
                    self._send_response(401, {"error": "Invalid credentials"})
            except Exception as e:
                self._send_response(500, {"error": str(e)})
        else:
            self._send_response(404)

    def do_GET(self):
        """处理数据请求"""
        parsed_path = urlparse(self.path)

        # 验证接口
        if parsed_path.path == '/auth/verify':
            return self.handle_verify()
        # 代理vnstat json接口
        elif parsed_path.path == '/json.cgi':
            return self._proxy_vnstat_json()
        elif parsed_path.path.startswith('/backups/'):
            # 验证Token
            if AUTH_ENABLED:
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