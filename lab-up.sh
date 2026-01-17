#!/bin/bash
# Lab Startup Script
# Brings all services online (NetBox, monitoring stack, poller)
# 
# FUTURE ENHANCEMENTS:
# - Add --init flag to run initialization (create buckets, provision Grafana)
# - Add health check loop to verify all services are ready before starting poller
# - Add --verify flag to run smoke tests after startup
# - Add startup time tracking and progress indicators
# - Consider rolling startup delays to stagger service startup load

echo "🚀 Starting NetDevOps Lab..."

# 1. Start Project 1 Containers (NetBox)
echo "--- Starting NetBox Source of Truth ---"
# NOTE: Waiting for NetBox to be ready before starting dependent services
cd ~/netbox-docker && docker compose up -d
echo "✅ NetBox Stack Started. Waiting for API to be ready..."
sleep 10  # Allow NetBox time to initialize

# 2. Start Project 2 Containers (Monitoring)
echo "--- Starting InfluxDB & Grafana ---"
# NOTE: Using `docker compose up -d` to start background services.
# FUTURE: Health check loop to verify InfluxDB is responding before starting poller
cd ~/netdevops-project2 && docker compose up -d
echo "✅ Monitoring Stack Started. Waiting for initialization..."
sleep 10  # Allow InfluxDB/Grafana to initialize

# 3. Start the ICMP Poller (System Service)
echo "--- Starting Python Poller Service ---"
# FUTURE: Verify InfluxDB health before starting to prevent early connection errors
sudo systemctl start net-poller.service
echo "✅ Poller Started."

echo "---------------------------------------"
echo "✨ All services are online!"
echo "Check status anytime with: docker ps"
echo "View poller logs: journalctl -u net-poller -f"
echo "Grafana: http://localhost:3000"
# FUTURE: Add optional verification loop to confirm all services are healthy
