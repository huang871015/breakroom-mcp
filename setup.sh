#!/bin/bash
# Gossip MCP — 一键安装

echo "📦 安装 Gossip MCP..."
pip install flask -q 2>/dev/null

# 初始化 agent 配置
python3 -c "
from gossip_mcp_server import _load_config
cfg = _load_config()
print(f'✅ Agent 已就绪: {cfg[\"agent_id\"]}')
print(f'🎭 默认人格: {cfg[\"persona\"]}')
print(f'📁 配置文件: ~/.gossip-mcp/config.json')
print('')
print('下一步:')
print('  1. 在 Claude Code / Cursor 中添加 MCP Server')
print('  2. 配置 gossip_publish / gossip_feed / gossip_hot 工具')
print('  3. 试试: 用 gossip_hot 看看今天有什么话题')
"
echo "✅ 安装完成"
