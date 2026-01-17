# 📊 Project 2: Automated Network Observability Stack
**Author:** Eric R. Rivera
**Status:** PRODUCTION READY ✅

## 🏗️ Architecture
This project implements an automated "closed-loop" monitoring system. The Python engine dynamically discovers inventory from NetBox and streams real-time telemetry to a time-series database.



### 🛠️ Core Components
* **Source of Truth:** NetBox (Dockerized) provides the list of active devices and management IPs.
* **Telemetry Store:** InfluxDB 2.7 stores high-resolution ICMP latency data.
* **Visualization:** Grafana Dashboards provide real-time NOC-style visibility.
* **Automation Engine:** A Python `systemd` service that handles non-privileged ICMP polling.

### 🚀 Management Commands
* **Check System Health:** `check-stack` (Custom alias for `verify_stack.py`)
* **Bulk Provision:** `python3 bulk_provision.py` (Idempotent device onboarding).
* **Restart Services:** `sudo systemctl restart net-poller`