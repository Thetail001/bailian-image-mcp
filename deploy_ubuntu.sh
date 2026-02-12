#!/bin/bash

# 阿里云百炼 MCP 服务 Ubuntu 一键部署/更新脚本
# 兼容性: Ubuntu 18.04+, Debian 10+
# 特点: 自动通过 uv 管理 Python 3.10+ 环境，无视系统 Python 版本过低问题

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/bailian-mcp"
SERVICE_NAME="bailian-mcp"
LOG_FILE="/var/log/bailian-mcp.log"
PACKAGE_NAME="bailian-imagegen-mcp-edited"

echo -e "${GREEN}=== 阿里云百炼 MCP 服务部署/更新工具 (UV 托管版) ===${NC}"

# 1. 权限检查
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}错误: 请以 root 权限运行此脚本 (使用 sudo)${NC}"
  exit 1
fi

# 2. 准备工作目录
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 3. 安装/检测 UV
echo -e "${YELLOW}--- 检查环境引擎 (uv) ---${NC}"
if ! command -v uv >/dev/null 2>&1 && [ ! -f "./uv" ]; then
    echo -e "${YELLOW}正在安装 uv 引擎以管理 Python 环境...${NC}"
    # 下载 uv 到安装目录
    curl -LsSf https://astral.sh/uv/install.sh | BINDIR=$INSTALL_DIR sh
fi

UV_BIN="./uv"
if command -v uv >/dev/null 2>&1; then
    UV_BIN="uv"
fi

# 4. 检测现有安装
if [ -f ".env" ] && [ -d "venv" ]; then
    echo -e "${YELLOW}检测到已安装的服务。${NC}"
    echo -e "1) 检查更新并重启"
    echo -e "2) 重新配置并重装"
    echo -e "3) 退出"
    read -p "选择操作 [1-3]: " choice
    case $choice in
        1)
            echo -e "${YELLOW}--- 正在检查更新... ---${NC}"
            $UV_BIN pip install -i https://pypi.org/simple --upgrade $PACKAGE_NAME
            systemctl restart $SERVICE_NAME
            echo -e "${GREEN}升级完成并已重启。${NC}"
            exit 0
            ;;
        2)
            echo -e "${YELLOW}重新配置...${NC}"
            ;;
        *)
            exit 0
            ;;
    esac
fi

# 5. 交互式配置
echo -e "\n${YELLOW}--- 配置阶段 ---${NC}"
read -p "请输入阿里云百炼 API Key (DASHSCOPE_API_KEY): " DASH_KEY
read -p "请输入自定义 MCP 访问 Token: " ACCESS_TOKEN
read -p "请输入运行端口 [默认 8000]: " S_PORT
S_PORT=${S_PORT:-8000}

# 6. 使用 UV 创建 Python 3.10 虚拟环境
echo -e "${YELLOW}--- 正在构建隔离的 Python 3.10+ 环境 (通过 uv) ---${NC}"
# uv 会自动下载合适的 Python 版本，不依赖系统 apt
$UV_BIN venv --python 3.10 venv

echo -e "${YELLOW}--- 安装程序包 ---${NC}"
$UV_BIN pip install -i https://pypi.org/simple $PACKAGE_NAME uvicorn

# 7. 写入配置
cat <<EOF > .env
DASHSCOPE_API_KEY=$DASH_KEY
MCP_ACCESS_TOKEN=$ACCESS_TOKEN
PORT=$S_PORT
EOF
chmod 600 .env

# 8. 创建 Systemd 服务
echo -e "${YELLOW}--- 配置 Systemd 服务 ---${NC}"
cat <<EOF > /etc/systemd/system/$SERVICE_NAME.service
[Unit]
Description=Aliyun Bailian Image Gen MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
# 使用 venv 中的 python 直接运行
ExecStart=$INSTALL_DIR/venv/bin/bailian-mcp-server --http --port \$PORT
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=multi-user.target
EOF

# 9. 日志管理
apt-get install -y logrotate >/dev/null 2>&1 || true
cat <<EOF > /etc/logrotate.d/$SERVICE_NAME
$LOG_FILE {
    size 10M
    rotate 5
    copytruncate
    compress
    missingok
    notifempty
}
EOF

# 10. 启动
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}部署成功!${NC}"
echo -e "环境运行在: $($INSTALL_DIR/venv/bin/python --version)"
echo -e "服务地址: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$S_PORT/mcp${NC}"
echo -e "实时日志: ${YELLOW}tail -f $LOG_FILE${NC}"
echo -e "${GREEN}==============================================${NC}"