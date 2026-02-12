#!/bin/bash

# 阿里云百炼 MCP 服务 Ubuntu 一键部署/更新脚本
# 适用系统: Ubuntu 20.04+, Debian 11+
# 注意: 本服务依赖 mcp SDK, 需要 Python 3.10+

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

echo -e "${GREEN}=== 阿里云百炼 MCP 服务部署/更新工具 ===${NC}"

# 1. 权限检查
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}错误: 请以 root 权限运行此脚本 (使用 sudo)${NC}"
  exit 1
fi

# 2. Python 版本检查与处理
echo -e "${YELLOW}--- 检查环境依赖 ---${NC}"
CHECK_PYTHON=$(python3 -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null || echo "False")

PY_CMD="python3"

if [ "$CHECK_PYTHON" == "False" ]; then
    echo -e "${YELLOW}检测到系统 Python 版本低于 3.10，正在尝试寻找/安装 Python 3.10...${NC}"
    if command -v python3.10 >/dev/null 2>&1; then
        PY_CMD="python3.10"
    else
        echo -e "${YELLOW}正在通过 deadsnakes PPA 安装 Python 3.10...${NC}"
        apt-get update
        apt-get install -y software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-distutils
        PY_CMD="python3.10"
    fi
fi

echo -e "${GREEN}使用 Python 解释器: $($PY_CMD --version)${NC}"

# 3. 检测现有安装
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}检测到已安装的服务目录: $INSTALL_DIR${NC}"
    echo -e "请选择操作:"
    echo -e "1) 检查更新并重启服务 (保持现有配置)"
    echo -e "2) 重新配置并覆盖安装 (修改 API Key/端口等)"
    echo -e "3) 退出"
    read -p "请输入序号 [1-3]: " choice

    case $choice in
        1)
            echo -e "${YELLOW}--- 正在检查版本更新... ---${NC}"
            # 确保 venv 存在
            if [ ! -f "$INSTALL_DIR/venv/bin/pip" ]; then
                echo -e "${RED}虚拟环境损坏，请选择 2 重新安装。${NC}"
                exit 1
            fi
            # 执行升级
            $INSTALL_DIR/venv/bin/pip install -i https://pypi.org/simple --upgrade $PACKAGE_NAME uvicorn
            NEW_VER=$($INSTALL_DIR/venv/bin/pip show $PACKAGE_NAME | grep Version | awk '{print $2}')
            echo -e "${GREEN}当前程序版本: $NEW_VER${NC}"
            echo -e "${YELLOW}--- 重启服务 ---${NC}"
            systemctl restart $SERVICE_NAME
            echo -e "${GREEN}服务已重启。${NC}"
            exit 0
            ;;
        2)
            echo -e "${YELLOW}进入重新配置模式...${NC}"
            ;;
        *)
            echo "操作取消。"
            exit 0
            ;;
    esac
fi

# 4. 交互式配置
echo -e "\n${YELLOW}--- 配置阶段 ---${NC}"
read -p "请输入阿里云百炼 API Key (DASHSCOPE_API_KEY): " DASH_KEY
while [ -z "$DASH_KEY" ]; do
    read -p "API Key 不能为空，请重新输入: " DASH_KEY
done

read -p "请输入您自定义的 MCP 访问 Token (用于客户端接入鉴权): " ACCESS_TOKEN
while [ -z "$ACCESS_TOKEN" ]; do
    read -p "Token 不能为空，请重新输入: " ACCESS_TOKEN
done

read -p "请输入服务运行端口 [默认 8000]: " S_PORT
S_PORT=${S_PORT:-8000}

# 5. 创建目录并准备环境
echo -e "${YELLOW}--- 准备工作目录: $INSTALL_DIR ---${NC}"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 重新创建虚拟环境以确保 Python 版本正确
echo -e "${YELLOW}--- 创建 Python 虚拟环境 (3.10+) ---${NC}"
rm -rf venv
$PY_CMD -m venv venv

echo -e "${YELLOW}--- 安装程序包 (来自 PyPI) ---${NC}"
./venv/bin/pip install -i https://pypi.org/simple --upgrade $PACKAGE_NAME uvicorn

# 6. 创建环境变量文件
cat <<EOF > .env
DASHSCOPE_API_KEY=$DASH_KEY
MCP_ACCESS_TOKEN=$ACCESS_TOKEN
PORT=$S_PORT
EOF
chmod 600 .env

# 7. 创建 Systemd 服务文件
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
ExecStart=$INSTALL_DIR/venv/bin/bailian-mcp-server --http --port \$PORT
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=multi-user.target
EOF

# 8. 配置日志轮转
echo -e "${YELLOW}--- 配置日志限额 (10MB x 5) ---${NC}"
apt-get install -y logrotate
cat <<EOF > /etc/logrotate.d/$SERVICE_NAME
$LOG_FILE {
    size 10M
    rotate 5
    copytruncate
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# 9. 启动服务
echo -e "${YELLOW}--- 启动服务 ---${NC}"
touch $LOG_FILE
chmod 644 $LOG_FILE
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}安装成功!${NC}"
echo -e "Python 版本: $($PY_CMD --version)"
echo -e "服务状态: ${YELLOW}systemctl status $SERVICE_NAME${NC}"
echo -e "服务地址: ${YELLOW}http://$(hostname -I | awk '{print $1}'):$S_PORT/mcp${NC}"
echo -e "访问 Token: ${YELLOW}$ACCESS_TOKEN${NC}"
echo -e "${GREEN}==============================================${NC}"
