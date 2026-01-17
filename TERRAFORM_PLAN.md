# Project 3: Terraform Infrastructure-as-Code Plan

## Overview

**Objective:** Codify Projects 1 & 2 infrastructure (NetBox, InfluxDB, Grafana) using Terraform to create a repeatable, version-controlled, and auditable infrastructure deployment.

**Scope:** Docker containers, volumes, networks, systemd services, environment configuration, and monitoring stack provisioning.

---

## 1. Terraform Architecture Recommendations

### Module Structure

Organize as three modules to mirror Projects 1 & 2:

```
terraform/
├── modules/
│   ├── netbox/
│   │   ├── main.tf            # NetBox Docker service (Project 1)
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── docker-compose.yml # or docker_service resource
│   ├── monitoring/
│   │   ├── main.tf            # InfluxDB + Grafana (Project 2)
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── docker-compose.yml
│   └── poller/
│       ├── main.tf            # health_poller systemd service
│       ├── variables.tf
│       ├── outputs.tf
│       └── poller.service
├── environments/
│   ├── dev.tfvars
│   ├── prod.tfvars
│   └── staging.tfvars
├── main.tf                    # Root module orchestration
├── variables.tf               # Root-level variables
├── outputs.tf                 # Root-level outputs
├── provider.tf                # Docker + local providers
└── terraform.tfvars          # Local overrides (gitignored)
```

### Provider Stack

```hcl
# provider.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}
```

**Rationale:**
- **Docker provider**: Manages containers, networks, volumes.
- **Local provider**: Renders systemd service files, .env templates, dashboard JSON.

---

## 2. Secret & Credential Management

### ⚠️ Critical: Never Store Secrets in State

**Problem:** Terraform state contains sensitive values (tokens, passwords).

**Solution Layers:**

#### Layer 1: Environment Variables (Development)
```bash
export TF_VAR_netbox_token="<your-token>"
export TF_VAR_influx_token="<your-token>"
export TF_VAR_grafana_admin_password="<password>"

terraform apply
```

#### Layer 2: .tfvars File (Local, Gitignored)
```hcl
# terraform.tfvars (NEVER commit)
netbox_token           = "abc123..."
influx_token           = "def456..."
grafana_admin_password = "secret"
```

Add to `.gitignore`:
```
terraform.tfvars
*.tfvars
!*.tfvars.example
```

#### Layer 3: Remote State with Encryption (Production)
Use S3 backend with:
- **Encryption at rest** (AWS KMS)
- **Encryption in transit** (TLS)
- **State locking** (DynamoDB)
- **Access controls** (IAM roles)

```hcl
# backend.tf (after initial apply)
terraform {
  backend "s3" {
    bucket         = "netdevops-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

#### Layer 4: Secret Manager Integration
For multi-team/CI/CD scenarios, use HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault:
```hcl
data "aws_secretsmanager_secret_version" "netbox_token" {
  secret_id = "netdevops/netbox/token"
}

locals {
  netbox_token = data.aws_secretsmanager_secret_version.netbox_token.secret_string
}
```

---

## 3. State Management Strategy

### Initial Setup (Single Developer)
```bash
# Initialize local state (no backend)
terraform init

# Plan and apply changes
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars

# Commit .terraform.lock.hcl (not .tfstate)
git add .terraform.lock.hcl
git commit -m "Add Terraform lock file"
```

**Gitignore:**
```
# Terraform
**/.terraform/
**/.terraform.lock.hcl          # ← OPTIONAL: can commit for reproducibility
terraform.tfstate
terraform.tfstate.backup
*.tfvars
!*.tfvars.example
crash.log
```

### Team Setup (Multiple Developers)
Migrate to remote backend with locking:
```bash
# After creating S3 bucket + DynamoDB table
terraform init -migrate-state

# Subsequent applies (automatic locking)
terraform apply
```

---

## 4. Module Design: Monitoring Stack

### Example: monitoring/main.tf

```hcl
# monitoring/main.tf
resource "docker_image" "influxdb" {
  name         = "influxdb:${var.influxdb_version}"
  keep_locally = true
}

resource "docker_image" "grafana" {
  name         = "grafana:${var.grafana_version}"
  keep_locally = true
}

resource "docker_volume" "influxdb_data" {
  name = "${var.project_name}-influxdb-data"
}

resource "docker_volume" "grafana_data" {
  name = "${var.project_name}-grafana-data"
}

resource "docker_network" "monitoring" {
  name = "${var.project_name}-monitoring"
}

resource "docker_container" "influxdb" {
  name    = "${var.project_name}-influxdb"
  image   = docker_image.influxdb.id
  restart_policy = "always"

  env = [
    "INFLUXDB_DB=${var.influx_database}",
    "INFLUXDB_HTTP_AUTH_ENABLED=true",
    "INFLUXDB_ADMIN_USER=${var.influx_admin_user}",
    "INFLUXDB_ADMIN_PASSWORD=${var.influx_admin_password}",
  ]

  networks_advanced {
    name = docker_network.monitoring.id
  }

  volumes {
    volume_name    = docker_volume.influxdb_data.name
    container_path = "/var/lib/influxdb"
  }

  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:8086/health"]
    interval     = "15s"
    timeout      = "5s"
    retries      = 5
    start_period = 20
  }
}

resource "docker_container" "grafana" {
  name    = "${var.project_name}-grafana"
  image   = docker_image.grafana.id
  restart_policy = "always"

  ports {
    internal = 3000
    external = var.grafana_port
  }

  env = [
    "GF_SECURITY_ADMIN_USER=${var.grafana_admin_user}",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_admin_password}",
    "INFLUX_URL=http://${docker_container.influxdb.name}:8086",
    "INFLUX_TOKEN=${var.influx_token}",
  ]

  networks_advanced {
    name = docker_network.monitoring.id
  }

  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }

  volumes {
    host_path      = "${path.module}/../grafana/provisioning"
    container_path = "/etc/grafana/provisioning"
    read_only      = true
  }

  depends_on = [docker_container.influxdb]

  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval     = "15s"
    timeout      = "5s"
    retries      = 5
  }
}
```

### Example: monitoring/variables.tf

```hcl
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "netdevops"
}

variable "influxdb_version" {
  description = "InfluxDB Docker image version"
  type        = string
  default     = "2.7.10"
}

variable "grafana_version" {
  description = "Grafana Docker image version"
  type        = string
  default     = "10.4.3"
}

variable "influx_database" {
  description = "InfluxDB database name"
  type        = string
  default     = "netdevops"
}

variable "influx_admin_user" {
  description = "InfluxDB admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "influx_admin_password" {
  description = "InfluxDB admin password"
  type        = string
  sensitive   = true
}

variable "influx_token" {
  description = "InfluxDB authentication token"
  type        = string
  sensitive   = true
}

variable "grafana_admin_user" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}

variable "grafana_port" {
  description = "Grafana external port"
  type        = number
  default     = 3000
}
```

### Example: monitoring/outputs.tf

```hcl
output "influxdb_container_id" {
  value       = docker_container.influxdb.id
  description = "InfluxDB container ID"
}

output "grafana_container_id" {
  value       = docker_container.grafana.id
  description = "Grafana container ID"
}

output "grafana_url" {
  value       = "http://localhost:${var.grafana_port}"
  description = "Grafana UI URL"
}

output "monitoring_network_id" {
  value       = docker_network.monitoring.id
  description = "Docker network ID for monitoring stack"
}
```

---

## 5. Poller Service Management

### Systemd Service via Terraform

Use `local_file` to render the systemd service file:

```hcl
# modules/poller/main.tf
resource "local_file" "poller_service" {
  filename = "/etc/systemd/system/net-poller.service"
  content  = templatefile("${path.module}/poller.service.tpl", {
    venv_path    = var.venv_path
    project_path = var.project_path
    poll_interval = var.poll_interval
  })

  provisioner "local-exec" {
    command = "sudo systemctl daemon-reload && sudo systemctl restart net-poller"
  }

  depends_on = [docker_container.influxdb, docker_container.grafana]
}
```

**Note:** Requires sudo or passwordless systemctl permissions. Consider alternative: Terraform `systemd_unit` resource from `bpg/systemd` provider for cleaner approach.

---

## 6. Environment Variable Rendering

### .env File Generation

```hcl
# modules/monitoring/main.tf
resource "local_file" "env_file" {
  filename = "${var.project_root}/.env"
  content  = <<-EOT
NETBOX_API_URL=${var.netbox_url}
NETBOX_API_TOKEN=${var.netbox_token}
INFLUXDB_URL=${var.influxdb_url}
INFLUXDB_ORG=${var.influx_org}
INFLUXDB_BUCKET=${var.influx_bucket}
INFLUXDB_TOKEN=${var.influx_token}
POLL_INTERVAL=${var.poll_interval}
EOT

  sensitive_content = true
}
```

**Rationale:** Ensures .env stays in sync with infrastructure; can regenerate on drift.

---

## 7. Networking & Tailscale Integration

### Tailscale Endpoint Discovery

For production, use data sources to discover Tailscale IPs:

```hcl
# Example: Fetch Tailscale IP from tag or subnet
variable "use_tailscale" {
  type    = bool
  default = true
}

variable "tailscale_ip" {
  type        = string
  description = "Tailscale private IP for service endpoint"
  default     = "100.89.136.43"
}

# In monitoring module
locals {
  influxdb_endpoint = var.use_tailscale ? "http://${var.tailscale_ip}:8086" : "http://localhost:8086"
}
```

### Docker Bridge Network Exposure

Ensure poller script uses Docker DNS (container name resolution) or bridge IP:

```hcl
resource "docker_network" "monitoring" {
  name   = "${var.project_name}-monitoring"
  driver = "bridge"
  ipam_config {
    subnet = "172.20.0.0/16"
  }
}

# In root main.tf outputs
output "influxdb_internal_url" {
  value = "http://${docker_container.influxdb.name}:8086"
}
```

---

## 8. Versioning & Pinning Strategy

### Best Practice: Pin Everything

```hcl
# Root terraform block
terraform {
  required_version = "~> 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.2"
    }
  }
}

# In modules/monitoring/main.tf
variable "influxdb_version" {
  default = "2.7.10"  # ← Pinned; never use "latest"
}

variable "grafana_version" {
  default = "10.4.3"   # ← Pinned
}
```

**Rationale:** Prevents unexpected updates; ensures reproducibility; aligns with docker-compose.yml pinning from Projects 1 & 2.

---

## 9. Validation & Testing Strategy

### Pre-Apply Validation

```bash
# Syntax check
terraform fmt -recursive
terraform validate

# Plan dry-run (shows what will change)
terraform plan -var-file=dev.tfvars -out=plan.out

# Review plan output before apply
terraform show plan.out

# Apply with plan
terraform apply plan.out
```

### Smoke Test Post-Apply

```bash
# Verify containers running
docker ps | grep netdevops

# Check InfluxDB health
curl http://localhost:8086/health

# Check Grafana health
curl http://localhost:3000/api/health

# Verify poller writes (requires running poller once)
./venv/bin/python health_poller.py --once
influx query 'from(bucket:"netdevops") |> range(start: -1h)'
```

### Automated Tests (Optional: Terraform Cloud/Enterprise)

```hcl
# tests/monitoring.tftest.hcl
run "influxdb_container_healthy" {
  command = plan

  assert {
    condition     = docker_container.influxdb.healthcheck[0].test[0] == "CMD"
    error_message = "InfluxDB healthcheck must use CMD format"
  }
}
```

---

## 10. Developer Workflow & UX

### Quick Start for New Developer

```bash
# 1. Clone repo + configure
git clone <repo>
cd netdevops-project2
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# ← Edit terraform.tfvars with your tokens

# 2. Initialize & apply
cd terraform
terraform init
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars

# 3. Verify services + start poller
docker ps
./venv/bin/python health_poller.py --once

# 4. Open Grafana
open http://localhost:3000
```

### Variable Precedence (for reference)

Terraform loads variables in this order (last wins):
1. Default values in `variables.tf`
2. `.tfvars` file
3. `-var` CLI flag
4. Environment variables (`TF_VAR_*`)

**Recommendation:** Use `.tfvars` for local dev; env vars for CI/CD.

---

## 11. Drift Detection & Recovery

### Detect Infrastructure Drift

```bash
# Plan against current state; shows unexpected changes
terraform plan

# If drift detected, either:
# Option A: Re-apply Terraform changes to match code
terraform apply

# Option B: Refresh state + inspect
terraform refresh
terraform state list
terraform state show 'docker_container.influxdb'

# Option C: Reimport manual changes
terraform import docker_container.influxdb <container-id>
```

### Prevent Drift: Lock Resources

```hcl
resource "docker_container" "influxdb" {
  # ... other config ...
  lifecycle {
    prevent_destroy = true
  }
}
```

---

## 12. Lessons from Projects 1 & 2: Apply to Terraform

| Lesson | Terraform Application |
|--------|----------------------|
| **Pin versions** | Use `= X.Y.Z` for image/provider versions; never use `latest` |
| **Env-based config** | Use `terraform.tfvars` + env vars for secrets; `.tfvars.example` for templates |
| **Healthchecks** | Include `healthcheck` blocks in all containers; use in `depends_on` with `condition` |
| **No hardcoding secrets in code** | Mark sensitive variables; use `.gitignore` for `*.tfvars` |
| **Logging & observability** | Enable Docker API debugging (`TF_LOG=DEBUG`); capture container logs |
| **Modular structure** | Split into `netbox`, `monitoring`, `poller` modules; reuse across environments |
| **Documentation** | README per module; explain `.tfvars` setup; provide demo path |

---

## 13. Next Steps Implementation Roadmap

### Phase 1: Project Scaffold (Week 1)
- [ ] Create `terraform/` directory structure
- [ ] Write root `provider.tf`, `main.tf`, `variables.tf`
- [ ] Draft `modules/monitoring/` (InfluxDB + Grafana)
- [ ] Create `.tfvars.example` with token placeholders
- [ ] Validate syntax: `terraform init` + `terraform validate`

### Phase 2: Secrets & State (Week 2)
- [ ] Implement secret handling (env vars + `.tfvars`)
- [ ] Test state file creation + gitignore
- [ ] Create S3 backend config (if team/prod)
- [ ] Document secret rotation procedures

### Phase 3: Modules & Outputs (Week 2)
- [ ] Complete `modules/netbox/` (Project 1 containers)
- [ ] Complete `modules/poller/` (systemd service rendering)
- [ ] Add `outputs.tf` with URLs and endpoints
- [ ] Test module reusability across environments

### Phase 4: Documentation & Demo (Week 3)
- [ ] Create `TERRAFORM_USAGE.md` (quick start guide)
- [ ] Record demo: `terraform init` → `apply` → `docker ps` → Grafana
- [ ] Add to portfolio README: "Infrastructure as Code with Terraform"
- [ ] Explain to interviewers: module design, state mgmt, secret handling

### Phase 5: CI/CD Integration (Optional, for advanced portfolio)
- [ ] Add GitHub Actions workflow: `terraform plan` on PR, `apply` on merge
- [ ] Integrate with Terraform Cloud for state locking + plan reviews
- [ ] Add cost estimation (`infracost`)

---

## 13a. Sprint Plan (time‑boxed)

Small sprints so you don’t work all night. Each sprint is ~30–90 minutes and builds on the previous one.

Sprint 0 — Setup (30–45 min)
- Create `terraform/` folders from the plan.
- Add `provider.tf`, minimal `main.tf`, and `.tfvars.example` with placeholders (gitignored real `.tfvars`).
- Run: `terraform init && terraform validate`.
- Decide state: local for dev; note S3+DynamoDB for team use (Section 3).

Sprint 1 — Monitoring module (InfluxDB + Grafana) (60–90 min)
- Implement `modules/monitoring` (images pinned, volumes, network, healthchecks).
- Inputs from `.tfvars`: `grafana_admin_password`, `influx_token`.
- Outputs: Grafana URL, network ID.
- `terraform plan -var-file=dev.tfvars` → `terraform apply`.
- Verify: `docker ps`, `curl :8086/health`, `curl :3000/api/health`.

Sprint 2 — NetBox module (45–60 min)
- Implement `modules/netbox` (image pin, volume, env, healthcheck).
- Output: NetBox URL.
- Apply and verify UI loads.

Sprint 3 — Poller module (45–60 min)
- Implement `modules/poller` using `local_file` (or `bpg/systemd` provider) to render `/etc/systemd/system/net-poller.service`.
- Provisioner: `systemctl daemon-reload && systemctl restart net-poller`.
- Verify: `systemctl status net-poller` and one-shot write `./venv/bin/python health_poller.py --once`.

Sprint 4 — Secrets & State hardening (30–45 min)
- Mark sensitive vars; ensure `.tfvars` is gitignored.
- Optional: migrate to S3 backend with locking (Section 2/3).
- Document token rotation and state backup.

Sprint 5 — Ansible starter for NetDevOps (Juniper) (45–60 min)
- Add `ansible.cfg` + NetBox inventory plugin and a simple playbook:
  - Pull devices from NetBox.
  - Ping or `facts` collection against lab Juniper devices (mock or a couple of real ones).
- Demo “inventory from NetBox” → “reachability”.

Sprint 6 — Polish (30–45 min)
- `terraform fmt -recursive`, `terraform validate`.
- Add `pre-commit` hooks (fmt/validate).
- Optional CI: GitHub Actions `terraform plan` on PR.

---

## 14. Portfolio Talking Points

**For Interviewers:**

1. **IaC Maturity:** "Progressed from docker-compose (manual, single-file) to Terraform (modular, versionable, audit trail)."
2. **Secrets Management:** "Learned NOT to commit `.tfvars` or state files; use environment variables + secret managers for prod."
3. **State Strategy:** "Implemented local state for dev + planned S3 backend with encryption for team environments."
4. **Module Reusability:** "Structured modules (netbox, monitoring, poller) to enable rapid environment creation (dev/staging/prod)."
5. **Operational Continuity:** "Terraform tracks all infrastructure changes; enables reproducible, disaster-recovery deployments."

---

## 15. Critical Checklist Before Commit

- [ ] `.gitignore` includes `terraform.tfvars`, `**/.terraform/`, `terraform.tfstate*`
- [ ] No hardcoded tokens/passwords in `.tf` files
- [ ] All variables marked `sensitive = true` for credentials
- [ ] `.tfvars.example` provided (no actual values)
- [ ] README includes quick-start: init → plan → apply
- [ ] Backend config documented (local vs. S3)
- [ ] `terraform fmt -recursive` passed
- [ ] `terraform validate` passed
- [ ] Tested `terraform plan` output for safety
- [ ] Tested `terraform apply` on clean VM/Docker host
- [ ] Container healthchecks included for all services

---

## 16. Ansible + NetBox Device Modeling Guidance (Juniper)

Should you model many devices now?
- Recommendation: start small and realistic, then scale.
- Begin with 6–10 devices across 2 sites, with roles that mimic your NOC:
  - core (EX/QFX), dist (EX), edge router (SRX), and a couple of access devices.
- Model in NetBox:
  - Sites, device roles, device types (Juniper SKUs), management interfaces, `primary_ip4`, and tags (e.g., `site=main-office`).

Benefits for Ansible:
- Use NetBox as inventory via `netbox.netbox.nb_inventory`.
- Juniper playbooks via `junipernetworks.junos` collection (facts, config pushes).
- Scale later to 20–50 devices once workflows are proven.

References:
- NetBox Inventory Plugin: https://docs.ansible.com/ansible/latest/collections/netbox/netbox/nb_inventory_inventory.html
- Juniper Ansible Collection: https://galaxy.ansible.com/junipernetworks/junos
- Ansible Network Guide: https://docs.ansible.com/ansible/latest/network/getting_started/index.html

---

## References

- [Terraform Docker Provider](https://registry.terraform.io/providers/kreuzwerker/docker/latest/docs)
- [Terraform State Best Practices](https://www.terraform.io/language/state)
- [Sensitive Variables](https://www.terraform.io/language/values/variables#sensitive-variables)
- [S3 Backend Configuration](https://www.terraform.io/language/settings/backends/s3)
- [Terraform Testing](https://developer.hashicorp.com/terraform/language/tests)

---

**Last Updated:** 2026-01-17  
**Status:** Ready for Phase 1 scaffolding  
**Assigned to:** User (manual Terraform implementation)
