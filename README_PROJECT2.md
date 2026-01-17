# 📊 Project 2: Automated Network Observability
**Lead Architect:** Eric R. Rivera
**Status:** COMPLETE ✅

## 🏗️ Architecture Overview
This project demonstrates a "closed-loop" automation system where the inventory (NetBox) dynamically drives the monitoring configuration.

### 🛠️ Key Components & Fundamentals
1. **Source of Truth (NetBox):** Used as the authoritative database for all network assets. 
   - *Concept:* Primary IP mapping ensuring management traffic is isolated from data traffic.
2. **Time-Series Historian (InfluxDB 2.7):** Optimized for high-velocity latency metrics.
   - *Concept:* Tags (Indexed metadata for filtering) vs. Fields (Raw numerical measurements).
3. **The Engine (Python Poller):**
   - *Automation:* Uses `pynetbox` for dynamic device discovery.
   - *Idempotency:* `bulk_provision.py` ensures infrastructure state matches the desired configuration without creating duplicates.
4. **Visualization (Grafana):** A single pane of glass for real-time latency and availability.

### 🚀 Key Technical Wins
- **Linux Kernel Tuning:** Configured `net.ipv4.ping_group_range` for non-privileged ICMP execution.
- **REST API Integration:** Implemented CRUD operations with schema validation and error handling.
- **Secret Management:** Utilized `.env` and `.gitignore` to protect API tokens.