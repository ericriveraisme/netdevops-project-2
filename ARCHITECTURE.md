# NetDevOps Project 2 - Architecture Overview

## Data Flow
- NetBox (SoT) holds devices with primary IPs.
- health_poller.py pulls active devices from NetBox, pings them, and writes `device_health` points to InfluxDB.
- Grafana reads InfluxDB with Flux and renders the provisioned dashboard (device status, latency, uptime, site aggregates, up/down counters).

## Components
- Python scripts: provisioning helpers (bulk_provision.py, bulk_ip_assign.py, get_slugs.py) and poller (health_poller.py).
- InfluxDB 2.7.x (pinned) for time series.
- Grafana 10.4.x (pinned) with provisioning for datasource and dashboard.
- Systemd service `net-poller` runs health_poller.py in venv (outside compose).

## Operational Notes
- Config via `.env`; required: NETBOX_URL/TOKEN, INFLUX_URL/TOKEN/ORG/BUCKET, GRAFANA_ADMIN_PASSWORD, POLL_INTERVAL.
- Poller CLI: `--once` for single run; `--interval` to override poll cadence. Handles SIGINT/SIGTERM gracefully.
- Docker healthchecks guard start order; avoid `docker compose down -v` if you want to keep Grafana/Influx data.

## Demo Tips (Interview)
- Run `./venv/bin/python health_poller.py --once` to generate fresh points, then refresh Grafana dashboard.
- Use dashboard filters (Site, Device) to scope views; top-line counters show quick status for non-technical viewers.
- Show provisioning helpers: run get_slugs.py to list slugs, bulk_provision.py to idempotently create sample devices.
