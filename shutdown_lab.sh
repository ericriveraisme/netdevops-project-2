#!/bin/bash
# Lab Shutdown Script
# Gracefully stops all services (poller, monitoring, NetBox)
# 
# FUTURE ENHANCEMENTS:
# - Add --force-reset flag for full teardown with `docker compose down -v` (destructive)
# - Add --terraform flag to call `terraform destroy` when Project 3 is scaffolded
# - Add timestamp logging to track shutdown history
# - Add verification step: retry status checks until all containers are stopped
# - Consider adding --backup flag to snapshot volumes before shutdown

echo "🛑 Starting Graceful Lab Shutdown..."

# 1. Stop the ICMP Poller (System Service)
echo "--- Stopping Python Poller Service ---"
# FUTURE: Consider polling systemctl status in a loop until stopped (with timeout)
sudo systemctl stop net-poller.service
echo "✅ Poller Stopped."

# 2. Stop Project 2 Containers (Monitoring)
echo "--- Stopping InfluxDB & Grafana ---"
# NOTE: Using `docker compose stop` to preserve volumes and data.
# FUTURE: When Terraform (Project 3) is scaffolded, add optional --terraform flag here
# to trigger `terraform destroy` for full IaC-managed teardown.
cd ~/netdevops-project2 && docker compose stop
echo "✅ Monitoring Stack Stopped."

# 3. Stop Project 1 Containers (NetBox)
echo "--- Stopping NetBox Source of Truth ---"
# FUTURE: Coordinate with Terraform destroy if using IaC for NetBox provisioning
cd ~/netbox-docker && docker compose stop
echo "✅ NetBox Stack Stopped."

echo "---------------------------------------"
echo "💤 All services are paused. Network traffic stopped."
echo "Check status anytime with: docker ps"
# FUTURE: Add optional verification loop to confirm all containers are in 'Exited' state