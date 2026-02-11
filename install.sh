#!/bin/bash
# Phone Agent 一键安装脚本
# 用法: bash install.sh

set -e

echo "🚀 Phone Agent 安装脚本"
echo "========================"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检测系统
detect_os() {
    if [ -d "/data/data/com.termux/files/home" ]; then
        echo "termux"
    elif [ -f "/etc/os-release" ]; then
        cat /etc/os-release | grep "^ID=" | cut -d= -f2
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "📱 检测系统: $OS"

# 安装依赖
install_deps() {
    echo ""
    echo "📦 安装依赖..."

    if [ "$OS" = "termux" ]; then
        pkg update -y
        pkg install -y python git wget curl

    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt update -y
        apt install -y python3 python3-pip git wget curl

    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum update -y
        yum install -y python3 git wget curl

    else
        echo -e "${YELLOW}⚠️ 未知系统，请手动安装依赖${NC}"
        echo "需要: python3, git, wget, curl"
    fi
}

# 安装 Python 依赖
install_python_deps() {
    echo ""
    echo "🐍 安装 Python 依赖..."

    pip3 install --upgrade pip 2>/dev/null || python3 -m pip install --upgrade pip 2>/dev/null || true

    pip3 install flask requests 2>/dev/null || python3 -m pip install flask requests 2>/dev/null || {
        echo -e "${RED}❌ Python 依赖安装失败${NC}"
        exit 1
    }

    echo -e "${GREEN}✅ Python 依赖安装完成${NC}"
}

# 下载 AutoJS
install_autojs() {
    echo ""
    echo "📥 检查 AutoJS..."

    AUTOJS_URL="https://github.com/hyb1996/Auto.js/releases"
    AUTOJS_APK=""

    # 检测架构
    if [ "$OS" = "termux" ]; then
        ARCH=$(uname -m)
        case "$ARCH" in
            aarch64)
                AUTOJS_APK="Auto.js-v6.0.18-arm64-v8a.apk"
                ;;
            armv7l|armhf)
                AUTOJS_APK="Auto.js-v6.0.18-armeabi-v7a.apk"
                ;;
            x86_64)
                AUTOJS_APK="Auto.js-v6.0.18-x86_64.apk"
                ;;
            x86|i386)
                AUTOJS_APK="Auto.js-v6.0.18-x86.apk"
                ;;
            *)
                echo -e "${YELLOW}⚠️ 未知架构: $ARCH，跳过 AutoJS${NC}"
                return 0
                ;;
        esac

        if [ ! -f "$HOME/$AUTOJS_APK" ]; then
            echo "📥 下载 AutoJS $ARCH 版本..."
            wget -q "https://github.com/hyb1996/Auto.js/releases/download/v6.0.18/$AUTOJS_APK" \
                -O "$HOME/$AUTOJS_APK" || {
                echo -e "${YELLOW}⚠️ AutoJS 下载失败，请手动安装${NC}"
                echo "下载地址: $AUTOJS_URL"
            }
        else
            echo "✅ AutoJS 已存在: $HOME/$AUTOJS_APK"
        fi

        echo ""
        echo "📱 请在手机上安装 AutoJS:"
        echo "   1. 复制 $HOME/$AUTOJS_APK 到手机"
        echo "   2. 安装 AutoJS"
        echo "   3. 开启无障碍服务"
    else
        echo -e "${YELLOW}⚠️ 非 Termux 环境，跳过 AutoJS${NC}"
    fi
}

# 克隆项目
clone_project() {
    echo ""
    echo "📥 克隆 Phone Agent 项目..."

    if [ -d "phone-agent" ]; then
        echo "📁 phone-agent 已存在，更新中..."
        cd phone-agent
        git pull
    else
        git clone https://github.com/openclaw-glasses/phone-agent.git
        cd phone-agent
    fi

    echo -e "${GREEN}✅ 项目已准备就绪${NC}"
}

# 检查安装
check_install() {
    echo ""
    echo "🔍 检查安装状态..."

    ERROR=0

    # Python
    if command -v python3 &> /dev/null; then
        echo "✅ Python: $(python3 --version)"
    else
        echo "❌ Python 未安装"
        ERROR=1
    fi

    # pip
    if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null; then
        echo "✅ pip: OK"
    else
        echo "❌ pip 未安装"
        ERROR=1
    fi

    # git
    if command -v git &> /dev/null; then
        echo "✅ Git: $(git --version | head -1)"
    else
        echo "❌ Git 未安装"
        ERROR=1
    fi

    # wget
    if command -v wget &> /dev/null; then
        echo "✅ wget: OK"
    else
        echo "❌ wget 未安装"
        ERROR=1
    fi

    if [ $ERROR -eq 1 ]; then
        echo ""
        echo -e "${RED}❌ 安装失败，请检查上述错误${NC}"
        exit 1
    fi
}

# 主流程
main() {
    echo "========================"
    echo ""
    echo "开始安装 Phone Agent..."
    echo ""

    install_deps
    install_python_deps
    install_autojs
    clone_project
    check_install

    echo ""
    echo "========================"
    echo -e "${GREEN}🎉 安装完成！${NC}"
    echo ""
    echo "📝 下一步:"
    echo "   1. cd phone-agent"
    echo "   2. bash start.sh"
    echo ""
    echo "📖 文档: https://github.com/openclaw-glasses/phone-agent"
}

main "$@"
