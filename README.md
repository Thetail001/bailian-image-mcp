# 阿里云百炼生图 MCP 服务器

一个 Model Context Protocol 服务器，提供阿里云百炼平台的图像生成和编辑功能。该服务器使LLM能够调用阿里云百炼API来生成、编辑图像，支持多种图像分辨率、多模型选择（Qwen, Z-Image, Wan系列）和自定义参数。

**最新功能：**
- **全异步架构**：完美适配 MCP SSE 协议，不会阻塞服务器心跳。
- **直接返回结果**：无需二次查询，生图请求直接返回图片 URL。
- **多模型支持**：支持 Qwen-Image, Wan (万相) 等最新模型。

## 可用工具

### `generate_image` - 生成图像 (同步返回)
使用文本提示词生成图像，请求等待生成完成后直接返回图片链接。
*   **必需**: `prompt`
*   **可选**: `model` (默认 z-image-turbo), `size` (默认 1024*1024), `prompt_extend`, `watermark`, `negative_prompt`

### `image_edit_generation` - 编辑图像 (同步返回)
基于现有图像和文本提示生成新的编辑版本。
*   **必需**: `prompt`, `image` (URL)
*   **可选**: `model` (默认 qwen-image-edit-plus), `negative_prompt`

### `list_image_models` - 获取模型列表
返回支持的图像模型列表及其详细说明（包括简介、分辨率限制等）。

## 快速开始

### 方式 1: 使用 uvx 直接运行 (推荐)
如果已安装 `uv`，无需下载代码即可运行：

```bash
# 需设置环境变量 DASHSCOPE_API_KEY
uvx --from bailian-imagegen-mcp-edited bailian-mcp-server
```

### 方式 2: 本地安装运行

```bash
# 安装包
pip install bailian-imagegen-mcp-edited

# 运行
bailian-mcp-server
```

## 配置指南

### 身份验证
您需要阿里云百炼平台的 API 密钥。
```bash
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 1. Claude.app 配置 (桌面版)
编辑配置文件 (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows: `%APPDATA%\Claude\claude_desktop_config.json`)：

```json
{
  "mcpServers": {
    "bailian-image": {
      "command": "uvx",
      "args": [
        "--from",
        "bailian-imagegen-mcp-edited",
        "bailian-mcp-server"
      ],
      "env": {
        "DASHSCOPE_API_KEY": "sk-your-real-api-key"
      }
    }
  }
}
```

### 2. 魔搭社区 (ModelScope) 部署配置
如果您在魔搭 MCP 广场创建服务，请使用以下配置：

*   **托管类型**: 可托管部署
*   **服务配置**:
    ```json
    {
      "mcpServers": {
        "bailian-image": {
          "command": "uvx",
          "args": [
            "--from",
            "bailian-imagegen-mcp-edited@latest",
            "bailian-mcp-server"
          ],
          "env": {
            "DASHSCOPE_API_KEY": "sk-your-real-api-key"
          }
        }
      }
    }
    ```

### 3. VS Code 配置 (Cline/Roo 等插件)
在项目根目录创建 `.vscode/mcp.json`：

```json
{
  "mcp": {
    "servers": {
      "bailian-image": {
        "command": "uvx",
        "args": [
          "--from",
          "bailian-imagegen-mcp-edited",
          "bailian-mcp-server"
        ],
        "env": {
            "DASHSCOPE_API_KEY": "sk-your-real-api-key"
        }
      }
    }
  }
}
```

## 开发与调试

如果您从源码运行：

```bash
# 安装依赖
pip install -e .

# Stdio 模式运行
python bailian_mcpserver.py

# HTTP/SSE 模式运行 (用于远程部署调试)
python bailian_mcpserver.py --http
```

### 调试
使用 MCP Inspector 进行调试：
```bash
npx @modelcontextprotocol/inspector python bailian_mcpserver.py
```

## 许可证
MIT License
