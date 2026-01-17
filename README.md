# 📊 Project 2: Automated Network Observability Stack
**Author:** Eric R. Rivera  
**Status:** PRODUCTION READY ✅  
**Version:** 1.1.0  
**Last Updated:** January 17, 2026

[![Security](https://img.shields.io/badge/security-best_practices-green.svg)](SECURITY.md)
[![Changelog](https://img.shields.io/badge/changelog-maintained-blue.svg)](CHANGELOG.md)

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Security & Credential Management](#security--credential-management)
- [Quick Start](#quick-start)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Career Relevance](#career-relevance)

## 🎯 Overview
This project implements an automated "closed-loop" monitoring system that demonstrates production-grade DevOps, NetDevOps, and Site Reliability Engineering (SRE) practices. The Python engine dynamically discovers network device inventory from NetBox (Source of Truth) and streams real-time ICMP telemetry to a time-series database for visualization and analysis.

**Key Achievement:** Successfully migrated from hardcoded credentials to enterprise-grade secret management, demonstrating security incident response and remediation capabilities.

## 🏗️ Architecture



### 🛠️ Core Components
* **Source of Truth:** NetBox (Dockerized) provides the list of active devices and management IPs.
* **Telemetry Store:** InfluxDB 2.7 stores high-resolution ICMP latency data.
* **Visualization:** Grafana Dashboards provide real-time NOC-style visibility.
* **Automation Engine:** A Python `systemd` service that handles non-privileged ICMP polling.

## 🔐 Security & Credential Management

This project implements **enterprise-grade security practices**:

### Secure Configuration
- ✅ **Centralized Secret Management:** All credentials stored in `.env` file (excluded from version control)
- ✅ **Environment Variable Injection:** Docker Compose uses `${VARIABLE}` syntax
- ✅ **Zero Hardcoded Credentials:** All Python scripts use `os.getenv()` for secure credential access
- ✅ **Template-Based Setup:** `.env.example` provides safe onboarding for new developers
- ✅ **Network Isolation:** Tailscale VPN (100.89.136.43) for private service communication

### Security Incident Response
**January 2026:** Successfully identified and remediated hardcoded credentials in git history:
- Rotated all exposed API tokens and passwords within 1 hour
- Implemented environment variable substitution across all services
- Documented incident in [SECURITY.md](SECURITY.md) following industry best practices
- See [CHANGELOG.md](CHANGELOG.md) for detailed timeline

**Learn More:** [SECURITY.md](SECURITY.md) | [CHANGELOG.md](CHANGELOG.md)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- NetBox instance (Project 1 or separate deployment)
- Tailscale VPN configured (optional but recommended)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd netdevops-project2
```

2. **Create/activate venv and install deps**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # dev/test (optional, includes pytest/ruff/black/mypy)
```

3. **Configure credentials (IMPORTANT)**
```bash
cp .env.example .env
# Edit .env with your actual credentials:
# - NETBOX_TOKEN (from NetBox Admin → API Tokens)
# - INFLUX_TOKEN (from InfluxDB → Data → API Tokens)
nano .env
```

4. **Start the monitoring stack**
```bash
docker compose up -d
```

5. **Verify deployment**
```bash
./venv/bin/python verify_stack.py
```

6. **Run the health poller**
```bash
./venv/bin/python health_poller.py          # continuous
./venv/bin/python health_poller.py --once   # single cycle
```

### Management Commands
* **Check System Health:** `./venv/bin/python verify_stack.py`
* **Bulk Provision Devices:** `./venv/bin/python bulk_provision.py` (Idempotent)
* **Discover NetBox Inventory:** `./venv/bin/python get_slugs.py`
* **Run tests:** `./venv/bin/python -m pytest -q`
* **Graceful Shutdown:** `./shutdown_lab.sh`

### Close-out Checklist (daily wrap-up)
* `docker compose ps` → both influxdb and grafana Up/healthy.
* `systemctl status net-poller` → running (if using service); or `./venv/bin/python health_poller.py --once` to validate writes.
* `./venv/bin/python -m pytest -q` → quick smoke of point shape.
* `git status -sb` → ensure `.env` and other secrets are untracked; no unexpected files staged.
* Avoid `docker compose down -v` if you want to retain Grafana/Influx data.

## 🛠️ Technologies Used

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Source of Truth** | NetBox | Network device inventory and IP address management |
| **Time-Series DB** | InfluxDB 2.7 | High-velocity metrics storage |
| **Visualization** | Grafana | Real-time dashboards and alerting |
| **Automation** | Python 3 | Orchestration and polling engine |
| **Containerization** | Docker Compose | Infrastructure as Code |
| **API Integration** | PyNetBox, InfluxDB Client | REST API clients |
| **Secret Management** | python-dotenv | Secure credential loading |
| **Network** | Tailscale | Private VPN mesh network |

## 📁 Project Structure

```
netdevops-project2/
├── .env                    # Secrets (NEVER commit)
├── .env.example           # Template for developers
├── .gitignore             # Protects sensitive files
├── docker-compose.yml     # Infrastructure as Code
├── health_poller.py       # Main polling engine
├── bulk_provision.py      # Idempotent device onboarding
├── bulk_ip_assign.py      # IP management automation
├── get_slugs.py           # Inventory discovery
├── verify_stack.py        # Health check utility
├── shutdown_lab.sh        # Graceful teardown
├── CHANGELOG.md           # Version history
├── SECURITY.md            # Security practices and incident log
└── README.md              # This file
```

## 💼 Career Relevance

This project demonstrates competencies for the following roles:

### Primary Roles
1. **Site Reliability Engineer (SRE)**
   - Observability stack implementation
   - Automated health monitoring
   - Incident response and remediation
   - Infrastructure as Code (Docker Compose)

2. **DevOps Engineer**
   - CI/CD-ready credential management
   - Container orchestration
   - Secret management best practices
   - Infrastructure automation

3. **Network Automation Engineer / NetDevOps**
   - NetBox integration (Source of Truth)
   - Dynamic inventory management
   - Network telemetry collection
   - ICMP polling without privileged access

4. **Platform Engineer**
   - Multi-service orchestration
   - API integration (REST)
   - Time-series data architecture
   - Microservices monitoring

5. **Cloud Engineer / Infrastructure Engineer**
   - Infrastructure as Code
   - Service mesh concepts (Tailscale)
   - Container-based deployments
   - Credential rotation procedures

### Key Skills Demonstrated
- ✅ **Security Awareness:** Credential management, incident response, security documentation
- ✅ **API Integration:** REST APIs (NetBox, InfluxDB)
- ✅ **Python Development:** Production-grade code with error handling
- ✅ **Infrastructure as Code:** Docker Compose, environment-driven configuration
- ✅ **Observability:** Metrics collection, storage, and visualization (Grafana)
- ✅ **Automation:** Idempotent operations, dynamic inventory
- ✅ **Documentation:** Changelog, security policies, inline comments
- ✅ **Version Control:** Git best practices, meaningful commits
- ✅ **Linux Administration:** Systemd services, kernel tuning
- ✅ **Networking:** TCP/IP, ICMP, VPNs (Tailscale)

### Certifications This Project Aligns With
- HashiCorp Certified: Terraform Associate (IaC principles)
- AWS Certified DevOps Engineer
- Certified Kubernetes Administrator (CKA) - Container orchestration
- Red Hat Certified Engineer (RHCE) - Automation
- Cisco DevNet Associate/Professional - Network automation

---

## 📝 License
This project is part of a professional portfolio demonstrating NetDevOps and SRE capabilities.

## 🤝 Contributing
This is a portfolio project. For inquiries, please contact the author.

---

**Author:** Eric R. Rivera  
**LinkedIn:** [Add your LinkedIn]  
**GitHub:** [Add your GitHub]