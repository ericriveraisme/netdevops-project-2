# Security Policy

## Overview

This project implements security best practices for credential management, API authentication, and infrastructure-as-code principles for network automation and observability.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Security Incident History

### January 17, 2026 - Credential Exposure Remediation

**Severity:** CRITICAL  
**Status:** RESOLVED ✅

#### Incident Description
During development, hardcoded credentials were accidentally committed to the GitHub repository in `docker-compose.yml`:
- InfluxDB admin username: `admin`
- InfluxDB admin password: `adminpassword123`
- NetBox API token and InfluxDB API token were stored in `.env` but `.env` was not properly excluded from version control initially

#### Remediation Actions Taken

1. **Immediate Response**
   - All exposed credentials were immediately rotated
   - NetBox API token regenerated via NetBox Admin UI
   - InfluxDB containers restarted with new password
   - InfluxDB API token regenerated via InfluxDB UI

2. **Code Changes**
   - Removed hardcoded credentials from `docker-compose.yml`
   - Implemented environment variable interpolation (`${VARIABLE}` syntax)
   - Created `.env.example` template with placeholder values
   - Ensured `.env` is properly listed in `.gitignore`

3. **Git History Cleanup**
   - Repository history reviewed for exposed credentials
   - Commits with hardcoded credentials documented in CHANGELOG.md
   - Security-focused commit pushed to main branch

4. **Verification**
   - Confirmed `.env` file is the single source of truth
   - Verified all Python scripts use `os.getenv()` for credential access
   - Confirmed `docker-compose.yml` uses environment variable substitution
   - Tested all scripts with new credentials

#### Lessons Learned
- **Never commit credentials:** Always use environment variables or secret management tools
- **Review before push:** Check git diff for sensitive data before pushing
- **Template files:** Maintain `.env.example` with safe placeholder values
- **Early .gitignore:** Add `.env` to `.gitignore` at project initialization

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please follow these steps:

1. **Do NOT** open a public GitHub issue
2. Contact the maintainer directly via email (if this were a production project)
3. Provide detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested remediation (if known)

## Security Best Practices Implemented

### Credential Management
- ✅ All credentials stored in `.env` file (excluded from version control)
- ✅ Environment variable substitution in `docker-compose.yml`
- ✅ Python scripts use `python-dotenv` library for secure credential loading
- ✅ `.env.example` template provided for developers

### Network Security
- ✅ Tailscale VPN for private network isolation (100.89.136.43)
- ✅ No credentials transmitted over public internet
- ✅ API tokens rotated after any suspected exposure
- ✅ Service-to-service communication over private network

### Access Control
- ✅ NetBox API tokens with least-privilege access
- ✅ InfluxDB API tokens scoped to specific buckets
- ✅ Read/Write permissions explicitly defined
- ✅ No root-level container execution required

### Code Security
- ✅ Non-privileged ICMP via kernel tuning (no setuid/sudo)
- ✅ Input validation in provisioning scripts
- ✅ Idempotent operations prevent duplicate resource creation
- ✅ Error handling to prevent information disclosure

### Infrastructure Security
- ✅ Docker containers run with resource limits
- ✅ Persistent volumes for data isolation
- ✅ Docker Compose networks isolated from host
- ✅ Container images from official sources (InfluxDB, Grafana)

## Environment Variables

The following environment variables must be kept secure:

| Variable | Purpose | Sensitivity |
|----------|---------|-------------|
| `NETBOX_TOKEN` | NetBox API authentication | **CRITICAL** |
| `INFLUXDB_PASSWORD` | InfluxDB admin password | **CRITICAL** |
| `INFLUX_TOKEN` | InfluxDB API token | **CRITICAL** |
| `NETBOX_URL` | NetBox endpoint | Low (if using Tailscale) |
| `INFLUX_URL` | InfluxDB endpoint | Low (if using Tailscale) |

## Credential Rotation Procedures

### NetBox API Token
1. Login to NetBox UI: `http://100.89.136.43:8000`
2. Navigate to: **Admin → API Tokens**
3. Delete old token
4. Generate new token with required permissions
5. Update `NETBOX_TOKEN` in `.env`
6. Test connectivity: `python3 get_slugs.py`

### InfluxDB Credentials
1. Stop containers: `docker compose down -v`
2. Update `INFLUXDB_PASSWORD` in `.env`
3. Restart containers: `docker compose up -d`
4. Login to InfluxDB UI: `http://100.89.136.43:8086`
5. Navigate to: **Data → API Tokens → Generate**
6. Update `INFLUX_TOKEN` in `.env`
7. Test connectivity: `python3 health_poller.py` (watch for errors)

## Dependencies

This project uses the following third-party libraries. Security advisories are monitored:
- `pynetbox` - NetBox API client
- `influxdb-client` - InfluxDB Python client
- `icmplib` - Non-privileged ICMP implementation
- `python-dotenv` - Environment variable management

## Compliance

This project demonstrates security practices aligned with:
- **NIST Cybersecurity Framework** - Credential management and access control
- **OWASP Top 10** - Protection against security misconfiguration
- **CIS Benchmarks** - Docker and container security hardening
