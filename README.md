# 阿里云百炼生图 MCP 服务器

一个 Model Context Protocol 服务器，提供阿里云百炼平台的图像生成和编辑功能。该服务器使LLM能够调用阿里云百炼API来生成、编辑图像，支持多种图像分辨率、多模型选择（Qwen, Z-Image, Wan系列）和自定义参数。

**本次更新亮点：**
- **全异步架构**：完美适配 MCP SSE 协议，不会阻塞服务器心跳。
- **直接返回结果**：无需二次查询，生图请求直接返回图片 URL。
- **多模型支持**：新增 Qwen-Image, Wan (万相) 系列等多个模型支持。

## 可用工具

### `generate_image` - 生成图像 (同步返回)

使用文本提示词生成图像，请求等待生成完成后直接返回图片链接。

**必需参数：**

- `prompt` (string): 正向提示词，描述期望生成的图像内容

**可选参数：**

- `model` (string): 指定模型，默认为 "z-image-turbo"。支持 "qwen-image-max", "wan2.2-t2i-plus" 等。详细列表请使用 `list_image_models` 查看。
- `size` (string): 输出图像分辨率，默认 "1024*1024"。支持格式如 "1024*1024", "1280*720" 等。
- `prompt_extend` (bool): 是否开启prompt智能改写，默认 true
- `watermark` (bool): 是否添加水印标识，默认 false
- `negative_prompt` (string): 反向提示词，描述不希望出现的内容

> **注意**：生成图片数量 (`n`) 现已强制为 1 张，不再支持自定义数量。

### `image_edit_generation` - 编辑图像 (同步返回)

基于现有图像和文本提示生成新的编辑版本。

**必需参数：**

- `prompt` (string): 编辑指令提示词
- `image` (string): 输入图像的URL

**可选参数：**

- `model` (string): 编辑模型，默认为 "qwen-image-edit-plus"。
- `negative_prompt` (string): 反向提示词

### `list_image_models` - 获取模型列表

返回支持的图像模型列表及其详细说明（包括简介、分辨率限制等）。

## 安装

### 使用 uv (推荐)

使用 [uv](https://docs.astral.sh/uv/) 时无需特定安装。我们将使用 [uvx](https://docs.astral.sh/uv/guides/tools/) 直接运行 MCP 服务器。

### 使用 pip

或者，您可以通过 pip 安装：

```bash
pip install -e .
```

安装后，可以作为脚本运行：

```bash
python bailian_mcpserver.py
```

## 配置

### 身份验证

您需要阿里云百炼平台的 API 密钥。建议通过环境变量配置：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 为 Claude.app 配置

将以下内容添加到您的 Claude 设置：

```json
{
  "mcpServers": {
    "bailian-image": {
      "command": "uvx",
      "args": [
        "--from",
        "my-mcp-servers",
        "bailian-mcp-server"
      ],
      "env": {
        "DASHSCOPE_API_KEY": "sk-your-api-key"
      }
    }
  }
}
```

### 为 VS Code 配置

在工作区中创建 `.vscode/mcp.json` 文件：

```json
{
  "mcp": {
    "servers": {
      "bailian-image": {
        "type": "stdio",
        "command": "uvx",
        "args": [
            "--from",
            "my-mcp-servers",
            "bailian-mcp-server"
        ],
        "env": {
            "DASHSCOPE_API_KEY": "sk-your-api-key"
        }
      }
    }
  }
}
```

## 示例交互

### 1. 查询可用模型

```json
{
  "name": "list_image_models",
  "arguments": {}
}
```

### 2. 生成图像

```json
{
  "name": "generate_image",
  "arguments": {
    "prompt": "一只可爱的橙色小猫坐在阳光明媚的窗台上",
    "model": "wan2.2-t2i-plus",
    "size": "1024*1024"
  }
}
```

响应（直接返回 URL）：

```json
{
  "image_url": "https://dashscope-result-cn-beijing.oss-cn-beijing.aliyuncs.com/...",
  "request_id": "req_87654321",
  "model": "wan2.2-t2i-plus"
}
```

### 3. 编辑图像

```json
{
  "name": "image_edit_generation",
  "arguments": {
    "prompt": "将猫的颜色改为白色",
    "image": "https://example.com/original_image.jpg",
    "model": "qwen-image-edit-plus"
  }
}
```

响应：

```json
{
  "image_url": "https://example.com/edited_image.jpg",
  "request_id": "req_11223344"
}
```

## 运行模式

该服务器支持两种运行模式：

### Stdio 模式 (默认)

```bash
python bailian_mcpserver.py
```

### HTTP 模式 (团队服务)

```bash
python bailian_mcpserver.py --http
```

## 调试

您可以使用 MCP 检查器来调试服务器：

```bash
npx @modelcontextprotocol/inspector python bailian_mcpserver.py
```

## 贡献

我们鼓励贡献来帮助扩展和改进阿里云百炼生图 MCP 服务器。

## 许可证

该项目采用 MIT 许可证。