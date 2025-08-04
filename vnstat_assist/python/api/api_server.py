import base64
import hmac
import json
import logging
import os
import time
import urllib.request
from hashlib import sha256

from flask import Flask, jsonify, make_response, render_template, request

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "secret_key": "secret_key",
    "auth_enable": 1,
    "expire_seconds": 3600,
    "user": {"username": "username", "password": "password"},
    "vnstat_api": "http://vnstat.102419.xyz:19327/json.cgi",
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
    config["auth_enable"] = int(
        os.getenv("VNA_AUTH_ENABLE", str(DEFAULT_CONFIG["auth_enable"]))
    )

    # 仅在启用认证时验证必要字段
    if config["auth_enable"] == 1:
        required_keys = ["secret_key", "user.username", "user.password"]
        for key in required_keys:
            parts = key.split(".")
            value = config
            for part in parts:
                value = value.get(part)
                if not value:
                    raise ValueError(f"环境变量 {key} 必须配置（当启用认证时）")

    # 检查 vnstat_api 是否有效
    if not config["vnstat_api"].startswith(("http://", "https://")):
        raise ValueError("VNSTAT_API_URL 必须包含协议（如 http:// 或 https://）")
    return config


# 加载配置
try:
    CONFIG = load_config_from_env()
    SECRET_KEY = CONFIG["secret_key"].encode()  # Convert to bytes for HMAC
    VALID_USER = CONFIG["user"]
    VNSTAT_PROXY_URL = CONFIG["vnstat_api"]
    EXPIRE_SECONDS = CONFIG["expire_seconds"]
    AUTH_ENABLED = CONFIG["auth_enable"]
    JSON_DIR = "/app/backups/json"  # 备份文件目录

    logger.info("配置加载成功")
    logger.info(f"VNSTAT API地址: {VNSTAT_PROXY_URL}")
    logger.info(f"认证启用: {AUTH_ENABLED}")
except Exception as e:
    logger.error(f"配置加载失败: {str(e)}")
    raise

# 创建Flask应用
app = Flask(__name__)


class JWTManager:
    @staticmethod
    def generate_token(username):
        """生成JWT Token"""
        header = json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        payload = json.dumps(
            {
                "sub": username,
                "exp": int(time.time()) + EXPIRE_SECONDS,
                "iat": int(time.time()),
            }
        ).encode()

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


def set_cors_headers(response):
    """设置CORS头"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Max-Age"] = "1728000"
    return response


# 登录路由
@app.route("/auth/login", methods=["POST", "OPTIONS"])
def login():
    """处理登录请求"""
    if request.method == "OPTIONS":
        response = make_response()
        return set_cors_headers(response)

    if not AUTH_ENABLED:
        # 直接生成Token无需验证用户
        token = JWTManager.generate_token(VALID_USER["username"])
        response = jsonify({"token": token, "expires_in": EXPIRE_SECONDS})
        return set_cors_headers(response)

    try:
        data = request.get_json()
        if (
            data.get("username") == VALID_USER["username"]
            and data.get("password") == VALID_USER["password"]
        ):
            token = JWTManager.generate_token(VALID_USER["username"])
            response = jsonify({"token": token, "expires_in": EXPIRE_SECONDS})
            return set_cors_headers(response)
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 验证路由
@app.route("/auth/verify", methods=["GET", "OPTIONS"])
def verify():
    """验证Token有效性"""
    if request.method == "OPTIONS":
        response = make_response()
        return set_cors_headers(response)

    if not AUTH_ENABLED:
        # 直接返回验证通过
        response = jsonify({"valid": True, "user": "anonymous"})
        return set_cors_headers(response)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"valid": False, "error": "Missing token"}), 401

    token = auth_header.split(" ")[1]
    verification = JWTManager.verify_token(token)

    if verification["valid"]:
        response = jsonify({"valid": True, "user": verification["payload"]["sub"]})
    else:
        response = jsonify(verification)

    return set_cors_headers(response)


# 代理路由
@app.route("/json.cgi", methods=["GET"])
def proxy_vnstat_json():
    """代理请求到vnstat的json.cgi接口"""
    if AUTH_ENABLED:
        # 验证Token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing authorization token"}), 401

        token = auth_header.split(" ")[1]
        verification = JWTManager.verify_token(token)
        if not verification["valid"]:
            return jsonify({"error": verification["error"]}), 401
    # 发起代理请求
    try:
        req = urllib.request.Request(VNSTAT_PROXY_URL)
        with urllib.request.urlopen(req) as response:
            data = response.read().decode("utf-8")
            json_data = json.loads(data)
            response = jsonify(json_data)
            return set_cors_headers(response)
    except urllib.error.URLError as e:
        logger.error(f"代理请求失败: {str(e)}")
        return jsonify({"error": f"Failed to proxy request: {str(e)}"}), 502
    except json.JSONDecodeError:
        logger.error("无效的JSON响应")
        return jsonify({"error": "Invalid JSON response from upstream"}), 502
    except Exception as e:
        logger.error(f"代理请求异常: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 备份文件路由
@app.route("/backups/<day>", methods=["GET"])
def get_backup(day):
    """获取备份文件"""
    if AUTH_ENABLED:
        # 验证Token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing authorization token"}), 401

        token = auth_header.split(" ")[1]
        verification = JWTManager.verify_token(token)
        if not verification["valid"]:
            return jsonify({"error": verification["error"]}), 401

    # 处理文件请求
    try:
        file_path = os.path.join(JSON_DIR, f"vnstat_{day}.json")

        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                content = json.load(f)
            return jsonify(content), 200
        else:
            return jsonify({"error": "File not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # 从环境变量获取端口号，默认为19328
    port = int(os.environ.get("PORT", 19328))
    logger.info(f"服务器启动于 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
