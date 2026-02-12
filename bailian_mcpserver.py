"""
Aliyun Bailian Image Generation MCP Server
Standardized SSE/Stdio implementation with Bearer Auth and Host Validation fix.
"""

import json
import os
import sys
import logging
from typing import Optional

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP, Context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# --- 1. 日志配置 (Linus 风格：只说重点) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("bailian-mcp")

# --- 2. 常量定义 ---
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
T2I_ENDPOINT = f"{BAILIAN_BASE_URL}/services/aigc/text2image/image-synthesis"
MULTIMODAL_ENDPOINT = f"{BAILIAN_BASE_URL}/services/aigc/multimodal-generation/generation"

# --- 3. 鉴权中间件 (保持简洁) ---
class MCPAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, access_token: str):
        super().__init__(app)
        self.access_token = access_token

    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        # 仅对 MCP 核心路径进行拦截
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization")
            if auth_header != f"Bearer {self.access_token}":
                logger.warning(f"Unauthorized access from {request.client.host}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid MCP Access Token"}
                )
        return await call_next(request)

# --- 4. 核心实例与安全设置 ---
mcp = FastMCP(
    name="Aliyun Bailian Image",
    instructions="Aliyun Bailian Image Generation/Editing via MCP"
)

# --- 5. 辅助逻辑 ---
def get_api_key() -> str:
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        logger.critical("DASHSCOPE_API_KEY is not set in environment!")
        sys.exit(1)
    return key

async def call_bailian_api(endpoint: str, payload: dict) -> dict:
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        if response.is_error:
            raise RuntimeError(f"Aliyun API Error ({response.status_code}): {response.text}")
        return response.json()

# --- 6. MCP 工具 (功能完整，逻辑清晰) ---

@mcp.tool()
async def list_image_models() -> str:
    """List available models and their descriptions."""
    return """
- Qwen Series: qwen-image-max, qwen-image-plus (Detail-rich)
- Z-Image Series: z-image-turbo (Fast, multi-res)
- Wan Series: wan2.2-t2i-plus, wan2.2-t2i-flash (Professional T2I)
- Editing: qwen-image-edit-plus
"""

@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = "z-image-turbo",
    size: str = "1024*1024",
    prompt_extend: Optional[bool] = None,
    watermark: bool = False,
    negative_prompt: Optional[str] = None,
) -> str:
    """Generate image using Bailian API."""
    is_multimodal = model.startswith("z-image")
    endpoint = MULTIMODAL_ENDPOINT if is_multimodal else T2I_ENDPOINT
    
    # 基础参数
    data = {
        "model": model,
        "input": {},
        "parameters": {
            "size": size, 
            "n": 1, 
            "watermark": watermark,
        },
    }

    # 只有显式设置且非 wan 系列时，才添加 prompt_extend
    # 因为 wan 系列传入此参数会报 InvalidParameter
    if prompt_extend is not None:
        if not model.startswith("wan"):
            data["parameters"]["prompt_extend"] = prompt_extend

    if is_multimodal:
        data["input"]["messages"] = [{"role": "user", "content": [{"text": prompt}]}]
        # z-image 的反向提示词在 parameters
        if negative_prompt:
            data["parameters"]["negative_prompt"] = negative_prompt
    else:
        data["input"]["prompt"] = prompt
        # wan/qwen 的反向提示词在 input
        if negative_prompt:
            data["input"]["negative_prompt"] = negative_prompt

    try:
        result = await call_bailian_api(endpoint, data)
        output = result.get("output", {})
        image_url = ""

        # 解析不同模型的响应结构
        if "results" in output and output["results"]:
            image_url = output["results"][0].get("url", "")
        elif "choices" in output and output["choices"]:
            msg_content = output["choices"][0].get("message", {}).get("content", [])
            if isinstance(msg_content, list) and msg_content and "image" in msg_content[0]:
                image_url = msg_content[0]["image"]

        if not image_url:
            return f"Error: No image URL in response. Raw: {json.dumps(result)}"

        return f"![Generated Image]({image_url})\n\nRequest ID: {result.get('request_id')}\n\n*Note: Do not modify the URL parameters.*"
    except Exception as e:
        return f"Execution Error: {str(e)}"

@mcp.tool()
async def image_edit_generation(
    prompt: str,
    image: str,
    model: str = "qwen-image-edit-plus",
    negative_prompt: Optional[str] = None,
    prompt_extend: bool = True,
) -> str:
    """Edit an image with prompt."""
    data = {
        "model": model,
        "input": {
            "messages": [{"role": "user", "content": [{"image": image}, {"text": prompt}]}]
        },
        "parameters": {"prompt_extend": prompt_extend}
    }
    if negative_prompt:
        data["parameters"]["negative_prompt"] = negative_prompt

    try:
        result = await call_bailian_api(MULTIMODAL_ENDPOINT, data)
        image_url = result["output"]["choices"][0]["message"]["content"][0]["image"]
        return f"![Edited Image]({image_url})\n\nRequest ID: {result.get('request_id')}"
    except Exception as e:
        return f"Execution Error: {str(e)}"

# --- 7. 入口控制 (干净利落) ---
def main():
    # 强制预检
    get_api_key()

    port = 8000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i+1])

    if "--http" in sys.argv:
        # 修复 421 Misdirected Request: 允许所有 Host 访问
        allowed = os.getenv("MCP_ALLOWED_HOSTS", "*:*")
        mcp.settings.transport_security.allowed_hosts = allowed.split(",")
        logger.info(f"Allowed hosts set to: {mcp.settings.transport_security.allowed_hosts}")

        app = mcp.streamable_http_app()
        
        access_token = os.getenv("MCP_ACCESS_TOKEN")
        if access_token:
            logger.info("Enabling Bearer Auth middleware")
            app.add_middleware(MCPAuthMiddleware, access_token=access_token)
        else:
            logger.warning("No MCP_ACCESS_TOKEN set. Service is UNPROTECTED.")

        logger.info(f"Serving MCP-over-SSE on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        logger.info("Serving MCP-over-Stdio")
        mcp.run()

if __name__ == "__main__":
    main()
