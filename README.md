# 阿里云百炼生图 MCP 服务器

一个 Model Context Protocol (MCP) 服务器，提供阿里云百炼平台的图像生成和编辑功能。该服务器支持 Stdio 和 HTTP/SSE 两种传输协议。

**最新更新 (v0.2.5)：**
- **架构切换**：采用标准 `sse_app` 架构，兼容性更强。
- **421 修复**：默认禁用 DNS Rebinding 保护，支持公网 IP/域名远程部署。
- **路径统一**：HTTP/SSE 连接路径统一为 `/sse`。
- **安全增强**：修复了 Bearer Auth 中间件对 SSE 路径的拦截逻辑。

## 可用工具

### `generate_image`
使用文本提示词生成图像。
*   **必需参数**: `prompt`
*   **可选参数**: `model` (默认 `z-image-turbo`), `size`, `prompt_extend`, `watermark`, `negative_prompt`

### `image_edit_generation`
基于现有图像和文本提示进行编辑。
*   **必需参数**: `prompt`, `image` (URL)

### `list_image_models`
获取所有支持的模型列表及详细说明。

## 部署与运行

### 1. Stdio 模式 (用于 Claude Desktop 等本地客户端)
直接通过 `uvx` 运行：
```bash
export DASHSCOPE_API_KEY="您的API_KEY"
uvx bailian-imagegen-mcp-edited
```

### 2. HTTP/SSE 模式 (远程服务器部署)
适用于将 MCP 服务器部署在 Linux 服务器上供远程连接。

```bash
# 安装
pip install bailian-imagegen-mcp-edited

# 运行 (默认端口 8000)
export DASHSCOPE_API_KEY="您的API_KEY"
export MCP_ACCESS_TOKEN="您的自定义Token"
bailian-mcp-server --http --port 8000
```

**连接信息：**
- **连接地址**: `http://<SERVER_IP>:<PORT>/sse`
- **鉴权方式**: HTTP Header 需包含 `Authorization: Bearer <MCP_ACCESS_TOKEN>`

## 客户端配置示例

### 远程连接配置 (适用于 Roo Code / Cline / Cursor 等)

在支持 MCP SSE 连接的客户端中，使用以下配置格式：

```json
{
  "mcpServers": {
    "bailian-image-remote": {
      "type": "sse",
      "url": "http://your-server-ip:8000/sse",
      "headers": {
        "Authorization": "Bearer YOUR_CUSTOM_TOKEN"
      }
    }
  }
}
```

> **注意**：如果未设置 `MCP_ACCESS_TOKEN`，则不需要 `headers` 字段。接入点路径必须是 `/sse`。

## 开发者调试

使用本地测试脚本验证连接性：
```bash
python tests/local_test.py
```

## 许可证
MIT
