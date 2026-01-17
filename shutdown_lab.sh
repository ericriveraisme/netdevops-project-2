#!/bin/bash

echo "🛑 Starting Graceful Lab Shutdown..."

# 1. Stop the ICMP Poller (System Service)
echo "--- Stopping Python Poller Service ---"
sudo systemctl stop net-poller.service
echo "✅ Poller Stopped."

# 2. Stop Project 2 Containers (Monitoring)
echo "--- Stopping InfluxDB & Grafana ---"
cd ~/netdevops-project2 && docker compose stop
echo "✅ Monitoring Stack Stopped."

# 3. Stop Project 1 Containers (NetBox)
echo "--- Stopping NetBox Source of Truth ---"
cd ~/netbox-docker && docker compose stop
echo "✅ NetBox Stack Stopped."

echo "---------------------------------------"
echo "💤 All services are paused. Network traffic stopped."
echo "Check status anytime with: docker ps"