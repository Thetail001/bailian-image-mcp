FROM python:3.11-slim

# 设置 pip 镜像源 (可选)
ARG PIP_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"

WORKDIR /app

# 复制项目文件
COPY pyproject.toml README.md bailian_mcpserver.py ./

# 安装依赖和当前包
RUN pip config set global.index-url $PIP_INDEX && \
    pip install --no-cache-dir .

# 暴露端口 (虽然 SSE 主要是出站/标准输入输出，但在 HTTP 模式下需要)
EXPOSE 8000

# 启动命令 (使用 pyproject.toml 中定义的入口点)
CMD ["bailian-mcp-server", "--http"]
