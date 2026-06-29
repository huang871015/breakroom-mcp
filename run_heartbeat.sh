#!/bin/bash
cd /Users/nister/Desktop/gossip-mcp
nohup python3 multi_agent_heartbeat.py > /tmp/hb.log 2>&1 &
echo "PID: $!"
sleep 3
tail -8 /tmp/hb.log
