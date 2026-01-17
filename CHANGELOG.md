# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-17

## [1.2.0] - 2026-01-17

### Added
- Requirements pinning (`requirements.txt`, `requirements-dev.txt`) and dev tools (pytest/ruff/black/mypy).
- Healthcheck and pinned image versions for InfluxDB and Grafana in `docker-compose.yml`.
- `ARCHITECTURE.md` to explain data flow and demo tips.
- Grafana dashboard enhancements for non-technical viewers (up/down counters, clearer titles/descriptions).

### Changed
- `health_poller.py` hardened: logging, env validation, NetBox timeouts, jittered intervals, graceful SIGINT/SIGTERM, safer ping handling.
- Provisioning helpers now log structured messages and reuse existing interfaces/IPs.
- README updated with venv-based setup, test command, and close-out checklist.

### Tests
- Added `tests/test_health_poller.py` point-shape smoke test; pytest passing in venv.

### Security
- **CRITICAL:** Removed hardcoded credentials from `docker-compose.yml` that were accidentally exposed in git history
- Migrated all sensitive credentials to centralized `.env` file with proper `.gitignore` protection
- Rotated all exposed API tokens and passwords:
  - NetBox API token regenerated
  - InfluxDB admin password regenerated
  - InfluxDB API token regenerated
- Implemented environment variable interpolation in `docker-compose.yml`
- Added `.env.example` template for secure credential management
- Updated all connection URLs to use Tailscale IP (100.89.136.43) for network isolation

### Added
- `.env.example` - Template file with documentation for all required environment variables
- `POLL_INTERVAL` - Configurable polling interval via environment variable (default: 30 seconds)
- `INFLUX_BUCKET` - Environment variable for InfluxDB bucket name consistency
- Security documentation in README and dedicated SECURITY.md file

### Changed
- `health_poller.py` - Now reads `POLL_INTERVAL` from environment instead of hardcoded 30 seconds
- `docker-compose.yml` - All credentials now use `${VARIABLE}` syntax from `.env`
- `.env` - Consolidated all credentials into single source of truth
- NetBox URL updated from localhost to Tailscale IP (100.89.136.43:8000)
- InfluxDB URL updated from localhost to Tailscale IP (100.89.136.43:8086)

### Fixed
- Removed duplicate `INFLUX_ORG` environment variable declaration
- Added missing `INFLUX_BUCKET` variable required by `health_poller.py`

---

## [1.0.0] - 2026-01-16

### Added
- Initial release of automated network observability stack
- NetBox integration for device inventory (Source of Truth)
- InfluxDB 2.7 for time-series telemetry storage
- Grafana dashboards for real-time visualization
- Python-based ICMP health polling engine
- Systemd service for persistent background polling
- Docker Compose orchestration for InfluxDB and Grafana
- Bulk device provisioning with idempotent operations
- IP address assignment automation
- Non-privileged ICMP execution via kernel tuning
- Custom `verify_stack.py` health check utility
- Graceful shutdown script for lab environment

### Documentation
- README.md - Project overview and architecture
- README_PROJECT2.md - Technical deep-dive and concepts
- Inline code comments and docstrings
