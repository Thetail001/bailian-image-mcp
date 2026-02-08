import asyncio
import os
import json
import sys
from unittest.mock import MagicMock

# 设置 API Key
os.environ["DASHSCOPE_API_KEY"] = ""

# 确保导入根目录模块
sys.path.insert(0, os.getcwd())

from bailian_mcpserver import generate_image

async def test_all_models():
    ctx = MagicMock()
    
    print("=== 测试 A: z-image-turbo (需走 Multimodal 接口 + messages) ===")
    res_z = await generate_image(
        ctx=ctx,
        prompt="A futuristic city in the style of cyberpunk, neon lights",
        model="z-image-turbo",
        size="1024*1024",
        prompt_extend=True # 测试开启思考过程
    )
    print(f"Z-Image 结果:\n{res_z}\n")

    print("=== 测试 B: wan2.2-t2i-flash (需走 T2I 接口 + prompt) ===")
    res_w = await generate_image(
        ctx=ctx,
        prompt="A beautiful mountain landscape during sunset, oil painting style",
        model="wan2.2-t2i-flash",
        size="1024*1024"
    )
    print(f"Wan 结果:\n{res_w}\n")

if __name__ == "__main__":
    asyncio.run(test_all_models())
