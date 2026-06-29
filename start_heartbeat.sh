#!/bin/bash
pkill -f heartbeat
sleep 2
cd /opt/promptmin
nohup python3 multi_agent_heartbeat.py > /tmp/heartbeat.log 2>&1 &
sleep 3
ps aux | grep heartbeat | grep -v grep
echo "---"
tail -8 /tmp/heartbeat.log
