# 阿里云百炼生图 MCP 服务器

一个 Model Context Protocol 服务器，提供阿里云百炼平台的图像生成和编辑功能。该服务器使LLM能够调用阿里云百炼API来生成、编辑图像，支持多种图像分辨率、多模型选择（Qwen, Z-Image, Wan系列）和自定义参数。

**最新功能：**
- **全异步架构**：完美适配 MCP SSE 协议，不会阻塞服务器心跳。
- **直接返回结果**：无需二次查询，生图请求直接返回图片 URL。
- **多模型支持**：支持 Qwen-Image, Wan (万相) 等最新模型。
- **安全保护**：支持 Bearer Token 鉴权，保护 HTTP/SSE 服务不被非法访问。

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

1. **阿里云 API 密钥** (必需): 
   用于调用百炼平台生图能力。
   ```bash
   export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   ```

2. **MCP 访问密钥** (可选，建议在 HTTP 模式下开启):
   用于保护 MCP 服务本身的安全性。开启后，客户端需在 Header 中提供 `Authorization: Bearer <token>`。
   ```bash
   export MCP_ACCESS_TOKEN="your_custom_secret_token"
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

# 1. Stdio 模式运行 (默认，本地使用)
python bailian_mcpserver.py

# 2. HTTP/SSE 模式运行 (用于服务器远程部署)
# 如果设置了 MCP_ACCESS_TOKEN，服务将受到鉴权保护
python bailian_mcpserver.py --http --port 8000
```

### 远程连接配置
当您在服务器部署并开启鉴权后，其他 MCP 客户端连接时需要配置 Header：

```json
{
  "mcpServers": {
    "bailian-image-remote": {
      "command": "curl",
      "args": [
        "-H", "Authorization: Bearer your_custom_secret_token",
        "http://your-server-ip:8000/mcp"
      ]
    }
  }
}
```
*(注意：具体客户端的配置方式可能有所不同，部分网关支持在 URL 后接参数或通过特定的环境变量传递 Token)*

### 调试
使用 MCP Inspector 进行调试：
```bash
npx @modelcontextprotocol/inspector python bailian_mcpserver.py
```

## 许可证
MIT License
