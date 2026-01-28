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
# 统一的生图/修图 Endpoint
GENERATION_ENDPOINT = f"{BAILIAN_BASE_URL}/services/aigc/multimodal-generation/generation"

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

qwen-image-max
简介：Max系列旗舰模型，提升图像真实感与自然度，降低AI痕迹，擅长人物质感、纹理细节和文字渲染。
输出规格：
格式：PNG
分辨率：支持可选分辨率（需通过size参数指定，如1024x1024）
图像数量：固定1张
特性：与qwen-image-max-2025-12-30能力相同。

qwen-image-plus
简介：Plus系列模型，擅长复杂文字渲染（如海报、对联），支持多样艺术风格。
输出规格：
格式：PNG
分辨率：支持可选分辨率（需通过size参数指定）
图像数量：固定1张

2. 图像编辑模型

qwen-image-edit-plus-2025-12-15
简介：支持单图编辑和多图融合，输出1–6张图像，支持自定义分辨率和提示词智能改写。
输出规格：
格式：PNG
分辨率：可指定（如1920x1080），默认接近1024x1024（基于输入图宽高比）

qwen-image-edit-plus-2025-10-30
简介：与上述型号功能相同，但版本日期不同。

qwen-image-edit
简介：基础编辑模型，仅支持输出1张图像，不支持自定义分辨率。
输出规格：
格式：PNG
分辨率：默认与输入图一致（不可指定）

二、Z-Image系列
1. 文生图模型

z-image-turbo
简介：轻量级模型，快速生成高质量图像，支持中英双语渲染，擅长复杂语义理解与多风格题材。
输出规格：
格式：PNG
分辨率：总像素范围512x512至2048x2048（需通过size参数指定宽高比）
图像数量：固定1张

三、Wan系列
1. 图像生成与编辑模型

wan2.6-image
简介：支持图像编辑和图文混排输出，适用于多图融合与风格迁移。
输出规格：
格式：PNG
分辨率：需通过size参数指定（如1280x1280）

wan2.2-t2i-flash
简介：极速版文生图模型，兼顾创意性与速度，支持自定义分辨率。
输出规格：
格式：PNG
分辨率：支持512x512至1440x1440的任意宽高组合

wan2.2-t2i-plus
简介：专业版文生图模型，优化创意性、稳定性和写实细节。
输出规格：与wan2.2-t2i-flash类似，但性能更优。
"""


@mcp.tool()
async def generate_image(
    ctx: Context,
    prompt: str,
    model: str = "z-image-turbo",
    size: str = "1024*1024",
    prompt_extend: bool = True,
    watermark: bool = False,
    negative_prompt: Optional[str] = None,
) -> str:
    """
    调用阿里云百炼生图API生成图像 (同步模式)

    Args:
        prompt: 正向提示词，用来描述生成图像中期望包含的元素和视觉特点
        model: 指定使用的图像生成模型，默认为 "z-image-turbo"。
               可用模型包括: "qwen-image-max", "qwen-image-plus", "z-image-turbo", "wan2.6-image", "wan2.2-t2i-flash", "wan2.2-t2i-plus" 等。
               详情请调用 list_image_models 工具查看。
        size: 输出图像的分辨率，格式为宽*高。默认为 "1024*1024"。
              不同模型支持的分辨率范围不同，请参考 list_image_models 的说明。
        prompt_extend: 是否开启prompt智能改写
        watermark: 是否添加水印标识
        negative_prompt: 反向提示词，用来描述不希望在画面中看到的内容

    Returns:
        包含图片URL的JSON格式字符串
    """
    try:
        api_key = get_api_key_from_context(ctx)
    except ValueError as e:
        return f"认证错误: {str(e)}"

    # 构建请求数据
    # 注意：所有推荐模型(Qwen/Z-Image/Wan)在 multimodal-generation 接口下通常支持 input.prompt 结构
    data = {
        "model": model,
        "input": {
            "prompt": prompt,
        },
        "parameters": {
            "size": size,
            "n": 1,  # 强制固定为1
            "prompt_extend": prompt_extend,
            "watermark": watermark,
        },
    }

    # 添加反向提示词（如果提供）
    if negative_prompt:
        data["input"]["negative_prompt"] = negative_prompt

    try:
        async with get_async_client(api_key) as client:
            response = await client.post(GENERATION_ENDPOINT, json=data)
            response.raise_for_status()
            result = response.json()

            # 同步接口直接返回结果
            if "output" in result:
                # 提取图片URL
                # 结构通常是 output: { results: [ { url: ... } ] } 或 output: { choices: [...] }
                # 阿里云新版接口通常统一在 output 中，但具体字段可能因模型而异
                
                # 尝试通用提取逻辑
                output = result["output"]
                image_url = ""
                
                if "results" in output and len(output["results"]) > 0:
                    image_url = output["results"][0].get("url", "")
                elif "choices" in output and len(output["choices"]) > 0:
                     # 部分模型可能返回 choices 结构
                     content = output["choices"][0].get("message", {}).get("content", [])
                     if content and isinstance(content, list) and "image" in content[0]:
                         image_url = content[0]["image"]
                
                if image_url:
                    return json.dumps(
                        {
                            "image_url": image_url,
                            "request_id": result.get("request_id", ""),
                            # 保留一些元数据供调试
                            "model": model
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                
                # 如果没找到标准URL，返回完整 output 供调试
                return f"未在响应中找到图片URL，完整响应: {json.dumps(result, ensure_ascii=False)}"
            
            else:
                return f"API响应错误: {result}"

    except httpx.RequestError as e:
        return f"请求错误: {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"HTTP错误: {e.response.status_code} - {e.response.text}"
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
            response = await client.post(GENERATION_ENDPOINT, json=data)
            response.raise_for_status()
            result = response.json()

            if "output" in result and "choices" in result["output"]:
                image_url = result["output"]["choices"][0]["message"]["content"][0]["image"]
                return json.dumps(
                    {
                        "image_url": image_url,
                        "request_id": result.get("request_id", ""),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
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
