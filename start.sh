#!/bin/bash
# Phone Agent 一键启动脚本
# 用法: bash start.sh

set -e

echo "🚀 Phone Agent 启动脚本"
echo "========================"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未安装${NC}"
        echo "请先运行: bash install.sh"
        exit 1
    fi
    echo "✅ Python: $(python3 --version)"
}

# 检查依赖
check_deps() {
    echo ""
    echo "🔍 检查依赖..."

    MISSING=0

    if ! python3 -c "import flask" 2>/dev/null; then
        echo "❌ Flask 未安装"
        MISSING=1
    else
        echo "✅ Flask: OK"
    fi

    if ! python3 -c "import requests" 2>/dev/null; then
        echo "❌ requests 未安装"
        MISSING=1
    else
        echo "✅ requests: OK"
    fi

    if [ $MISSING -eq 1 ]; then
        echo ""
        echo "请运行: bash install.sh"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    echo ""
    echo "📋 检查配置..."

    if [ ! -f "config.json" ]; then
        echo "📄 创建默认配置..."
        cat > config.json << 'EOF'
{
  "server": {
    "host": "0.0.0.0",
    "port": 50001
  },
  "adb": {
    "enabled": true,
    "wireless_ip": null
  },
  "autojs": {
    "enabled": false,
    "url": "http://127.0.0.1:8088"
  },
  "update_interval": null
}
EOF
        echo "✅ config.json 已创建"
    else
        echo "✅ config.json 已存在"
    fi
}

# 获取端口
get_port() {
    PORT=$(python3 -c "import json; print(json.load(open('config.json'))['server']['port'])" 2>/dev/null || echo "50001")
    echo "$PORT"
}

# 检查端口是否占用
check_port() {
    PORT=$1
    echo ""
    echo "🔌 检查端口 $PORT..."

    if command -v lsof &> /dev/null; then
        if lsof -i:$PORT &> /dev/null; then
            echo -e "${YELLOW}⚠️ 端口 $PORT 已被占用${NC}"
            read -p "是否继续? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            echo "✅ 端口 $PORT 可用"
        fi
    else
        echo "✅ 跳过端口检查"
    fi
}

# 获取本机 IP
get_ip() {
    if command -v ip &> /dev/null; then
        ip route get 1 &> /dev/null && ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "127.0.0.1"
    elif command -v ifconfig &> /dev/null; then
        ifconfig | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "127.0.0.1"
    else
        echo "127.0.0.1"
    fi
}

# 启动服务
start_server() {
    PORT=$(get_port)
    IP=$(get_ip)

    echo ""
    echo "========================"
    echo -e "${GREEN}🚀 启动 Phone Agent...${NC}"
    echo ""
    echo "📡 服务地址: http://$IP:$PORT"
    echo "📱 手机访问: http://$(get_ip):$PORT"
    echo ""
    echo "📖 API 文档: https://github.com/openclaw-glasses/phone-agent"
    echo ""
    echo "🛑 按 Ctrl+C 停止服务"
    echo "========================"
    echo ""

    # 启动
    exec python3 phone_agent.py
}

# 主流程
main() {
    check_python
    check_deps
    check_config

    PORT=$(get_port)
    check_port $PORT

    # 启动
    start_server
}

main "$@"
