#!/bin/bash
# PersBot 启动脚本
# 自动检查并安装所需的 MCP 服务器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 需要安装的 MCP 服务器列表
# 在这里添加你需要的服务器
MCP_SERVERS=(
    # "@anthropic/mcp-server-weather"
    # "@anthropic/mcp-server-brave-search"
    # "@anthropic/mcp-server-filesystem"
)

# 检查 node_modules 是否存在
check_and_install() {
    local package=$1
    
    if [ ! -d "node_modules/$package" ]; then
        echo -e "${YELLOW}📦 Installing $package...${NC}"
        npm install "$package" --save
        echo -e "${GREEN}✅ Installed $package${NC}"
    else
        echo -e "${GREEN}✅ $package already installed${NC}"
    fi
}

# 初始化 package.json（如果不存在）
if [ ! -f "package.json" ]; then
    echo -e "${YELLOW}📝 Initializing package.json...${NC}"
    npm init -y > /dev/null 2>&1
fi

# 安装 MCP 服务器
echo -e "${GREEN}🔧 Checking MCP servers...${NC}"
for server in "${MCP_SERVERS[@]}"; do
    if [ -n "$server" ]; then
        check_and_install "$server"
    fi
done

# 启动 Python 后端
echo -e "${GREEN}🚀 Starting PersBot backend...${NC}"
python main.py
