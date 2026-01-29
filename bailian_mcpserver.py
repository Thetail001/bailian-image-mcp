"""
阿里云百炼生图API MCP服务器

此MCP服务器提供调用阿里云百炼平台生图API的工具。
"""

import json
import os
import sys
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP, Context
from starlette.datastructures import Headers

# 阿里云百炼baseurl
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
# 文生图 Endpoint (z-image, wan, qwen-image)
T2I_ENDPOINT = f"{BAILIAN_BASE_URL}/services/aigc/text2image/image-synthesis"
# 多模态/修图 Endpoint (qwen-image-edit)
MULTIMODAL_ENDPOINT = f"{BAILIAN_BASE_URL}/services/aigc/multimodal-generation/generation"

# 创建全局MCP实例
mcp = FastMCP(name="阿里云百炼生图API MCP服务器")


def get_api_key_from_context(ctx: Context) -> str:
    """从MCP请求上下文或环境变量中获取API密钥"""

    # 1. 优先从环境变量获取
    env_key = os.getenv("DASHSCOPE_API_KEY")
    if env_key:
        return env_key

    # 2. 尝试从请求头获取 (兼容部分支持 request_context 的环境)
    # 注意：标准 MCP SDK 可能不包含 request_context，此逻辑仅为特定网关保留
    if hasattr(ctx, "request_context") and ctx.request_context:
        try:
            headers: Headers = ctx.request_context.request.headers
            if "Authorization" in headers:
                return headers["Authorization"][7:]  # 移除 "Bearer " 前缀
        except Exception:
            pass

    raise ValueError(
        "未找到有效的API密钥。请设置 DASHSCOPE_API_KEY 环境变量。"
    )


def get_async_client(api_key: str) -> httpx.AsyncClient:
    """获取异步HTTP客户端"""
    return httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # 移除 "X-DashScope-Async": "enable" 以使用同步模式
        },
        timeout=120.0,  # 同步生图可能耗时较长，设置 120秒 超时
    )


@mcp.tool()
async def list_image_models() -> str:
    """
    获取可用的阿里云百炼图像模型列表及其说明

    Returns:
        包含模型名称、简介和输出规格的详细文本
    """
    return """
一、Qwen系列图像模型
1. 图像生成模型
qwen-image-max / qwen-image-plus: 旗舰级模型，擅长细节和文字渲染。固定输出1张。

2. 图像编辑模型
qwen-image-edit-plus: 支持单图编辑和多图融合。

二、Z-Image系列 (文生图)
z-image-turbo: 轻量级极速模型，支持中英双语。
- 接口类型: Multimodal Generation
- 分辨率限制: 总像素范围 [512*512, 2048*2048]
- 推荐分辨率 (效果最佳):
  * 1:1 : 1024*1024, 1280*1280, 1536*1536
  * 2:3 : 832*1248, 1024*1536, 1248*1872
  * 3:2 : 1248*832, 1536*1024, 1872*1248
  * 9:16: 720*1280, 864*1536, 1152*2048
  * 16:9: 1280*720, 1536*864, 2048*1152

三、Wan系列 (通义万相)
wan2.2-t2i-plus / wan2.2-t2i-flash: 专业级/极速级文生图模型。
- 接口类型: Text2Image Synthesis
- 分辨率: 支持 512x512 至 1440x1440 任意组合。
"""


@mcp.tool()
async def generate_image(
    ctx: Context,
    prompt: str,
    model: str = "z-image-turbo",
    size: str = "1024*1024",
    prompt_extend: Optional[bool] = None,
    watermark: bool = False,
    negative_prompt: Optional[str] = None,
) -> str:
    """
    调用阿里云百炼生图API生成图像 (同步模式)

    Args:
        prompt: 正向提示词
        model: 指定使用的图像生成模型，默认为 "z-image-turbo"
        size: 输出图像的分辨率，默认 "1024*1024"
        prompt_extend: 是否开启prompt智能改写 (部分模型可能不支持，建议仅在明确需要时设置)
        watermark: 是否添加水印标识
        negative_prompt: 反向提示词

    Returns:
        包含图片URL的JSON格式字符串，或包含详细错误信息的JSON
    """
    try:
        api_key = get_api_key_from_context(ctx)
    except ValueError as e:
        return f"认证错误: {str(e)}"

    # 确定 Endpoint 和 Payload 结构
    # 策略:
    # 1. z-image 系列: 使用 multimodal 接口，参数为 input.messages
    # 2. wan 系列 / qwen-image 系列: 使用 text2image 接口，参数为 input.prompt
    
    endpoint = T2I_ENDPOINT
    payload_type = "prompt"  # prompt or messages
    
    if model.startswith("z-image"):
        endpoint = MULTIMODAL_ENDPOINT
        payload_type = "messages"
    
    # 构建请求数据
    data = {
        "model": model,
        "input": {},
        "parameters": {
            "size": size,
            "n": 1,
            "watermark": watermark,
        },
    }

    if payload_type == "messages":
        data["input"]["messages"] = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
    else:
        data["input"]["prompt"] = prompt

    # 仅当显式提供 prompt_extend 时才添加到参数中
    # 注意：Multimodal 接口通常支持 prompt_extend，但 T2I 的 wan 系列不支持
    if prompt_extend is not None:
        data["parameters"]["prompt_extend"] = prompt_extend

    if negative_prompt:
        if payload_type == "messages":
            # Multimodal 接口通常不支持直接的 input.negative_prompt，或者在 parameters 里
            # 根据经验，z-image 这里的 negative_prompt 比较复杂，暂且尝试放在 parameters
            # 或者 input.negative_prompt (如果文档支持)
            # z-image 文档: parameters.negative_prompt (String)
            data["parameters"]["negative_prompt"] = negative_prompt
        else:
            data["input"]["negative_prompt"] = negative_prompt

    try:
        async with get_async_client(api_key) as client:
            response = await client.post(endpoint, json=data)
            
            # ... (后续处理保持不变) ...
            if response.is_error:
                error_detail = response.text
                try:
                    # 尝试解析 JSON 错误信息使其更易读
                    error_json = response.json()
                    if "code" in error_json and "message" in error_json:
                        return json.dumps({
                            "status": "error",
                            "code": error_json.get("code"),
                            "message": error_json.get("message"),
                            "request_id": error_json.get("request_id")
                        }, ensure_ascii=False)
                except:
                    pass
                return f"API请求失败 (HTTP {response.status_code}): {error_detail}"

            result = response.json()

            # 同步接口直接返回结果
            if "output" in result:
                # 提取图片URL
                output = result["output"]
                image_url = ""
                
                if "results" in output and len(output["results"]) > 0:
                    image_url = output["results"][0].get("url", "")
                elif "choices" in output and len(output["choices"]) > 0:
                     content = output["choices"][0].get("message", {}).get("content", [])
                     if content and isinstance(content, list) and "image" in content[0]:
                         image_url = content[0]["image"]
                
                if image_url:
                    response_data = {
                        "image_url": image_url,
                        "request_id": result.get("request_id", ""),
                        "model": model
                    }
                    if "reasoning_content" in output.get("choices", [{}])[0].get("message", {}):
                        response_data["reasoning"] = output["choices"][0]["message"]["reasoning_content"]
                    
                    # 使用 Markdown 图片格式 + 显式指令
                    # 这里的指令是给 LLM 看的，要求它不要自作聪明地修改 URL
                    return f"""![Generated Image]({image_url})

**注意**：上图链接包含必要的签名参数，请直接原样展示，**不要修改链接中的任何字符**，否则会导致图片无法显示。

调试信息:
{json.dumps(response_data, ensure_ascii=False, indent=2)}"""
                
                return f"未在响应中找到图片URL，完整响应: {json.dumps(result, ensure_ascii=False)}"
                
                return f"未在响应中找到图片URL，完整响应: {json.dumps(result, ensure_ascii=False)}"
            
            else:
                return f"API响应错误: {json.dumps(result, ensure_ascii=False)}"

    except httpx.RequestError as e:
        return f"网络请求错误: {str(e)}"
    except Exception as e:
        return f"生成图像时发生未知错误: {str(e)}"


@mcp.tool()
async def image_edit_generation(
    ctx: Context,
    prompt: str,
    image: str,
    model: str = "qwen-image-edit-plus",
    negative_prompt: Optional[str] = None,
) -> str:
    """
    调用阿里云百炼编辑图片API生成图像 (同步模式)

    :param prompt: 正向提示词
    :param image: 输入图像的URL或Base64
    :param model: 指定使用的图像编辑模型，默认为 "qwen-image-edit-plus"
    :param negative_prompt: 反向提示词
    
    Returns:
        包含生成的图像URL的JSON
    """
    try:
        api_key = get_api_key_from_context(ctx)
    except ValueError as e:
        return f"认证错误: {str(e)}"

    # 构建请求数据
    data = {
        "model": model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": image,
                        },
                        {"text": prompt},
                    ],
                }
            ]
        },
        "parameters": {
            "prompt_extend": True,
            "watermark": False,
        },
    }

    if negative_prompt:
        data["parameters"]["negative_prompt"] = negative_prompt

    try:
        async with get_async_client(api_key) as client:
            response = await client.post(MULTIMODAL_ENDPOINT, json=data)
            response.raise_for_status()
            result = response.json()

            if "output" in result and "choices" in result["output"]:
                image_url = result["output"]["choices"][0]["message"]["content"][0]["image"]
                
                return f"""![Edited Image]({image_url})

**注意**：请直接原样展示上方图片链接，**不要修改 URL 中的任何参数**（如 Signature 等），否则图片将无法加载。

Request ID: {result.get("request_id", "")}"""
            else:
                return f"API响应错误: {result}"

    except httpx.RequestError as e:
        return f"请求错误: {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"HTTP错误: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"编辑图像时发生未知错误: {str(e)}"


# 支持两种模式的启动脚本
def main():
    if "--http" in sys.argv:
        # stdio 模式下不要打印到 stdout
        print("启动HTTP模式（团队服务模式）") 
        mcp.run(transport="streamable-http")
    else:
        # 打印到 stderr 是安全的
        print("启动stdio模式（个人使用模式）", file=sys.stderr)
        mcp.run()

if __name__ == "__main__":
    main()
