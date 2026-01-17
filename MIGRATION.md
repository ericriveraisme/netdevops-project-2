# Cloud Migration Guide: Laptop → Oracle Cloud / DigitalOcean

## Overview

**Objective:** Migrate the NetDevOps monitoring stack from local laptop VM to cloud-hosted infrastructure using the free-to-cheap path.

**Target Providers:**
- **Oracle Cloud Infrastructure (OCI)**: Forever-free tier (4 ARM cores, 24GB RAM)
- **DigitalOcean**: Low-cost VPS ($6–$24/month)

**Migration Strategy:** Incremental, Terraform-driven, reversible.

---

## Kubernetes vs k3s for NetDevOps

### What's the Difference?

| Feature | Kubernetes (k8s) | k3s |
|---------|------------------|-----|
| **Size** | ~1GB binary + etcd | ~50MB binary, SQLite default |
| **Memory** | 2GB+ per node min | 512MB–1GB per node |
| **Components** | etcd, cloud-controller-manager, full feature set | Embedded SQLite/etcd, stripped cloud-controllers |
| **Installation** | kubeadm, kops, managed (GKE/EKS) | Single binary install |
| **Use Case** | Enterprise multi-tenant, cloud-native apps | Edge, IoT, small clusters, resource-constrained |
| **Maintenance** | Complex upgrades, HA setup | Simple upgrades, single-node or HA |

### Why k3s for NetDevOps?

**Reasons to Choose k3s:**
1. **Resource Efficiency**: NetDevOps workloads (NetBox, InfluxDB, Grafana, poller) don't need full k8s overhead.
2. **Single-Node Friendly**: Run on one Oracle Cloud VM (4 cores, 24GB RAM) and still have room for apps.
3. **Fast Setup**: `curl -sfL https://get.k3s.io | sh -` → cluster ready in 60 seconds.
4. **Edge-Optimized**: Perfect for distributed NOC monitoring (remote sites, branch offices).
5. **Cost**: Free Oracle tier or $6/month DO droplet vs. $75+ for managed k8s.

**When Full k8s Makes Sense:**
- Multi-tenant SaaS with 10+ teams.
- 1,000+ devices across 50+ sites (need horizontal pod autoscaling at massive scale).
- Cloud-native integrations (AWS ALB Ingress, GCP CloudSQL Proxy).
- Compliance/audit requirements for full k8s API conformance.

**For Your Project:** k3s is the sweet spot. You get orchestration, HA, auto-restart, and service discovery without the bloat.

---

## Migration Path Overview

```
Phase 1: Laptop VM (Current)
  └─ Docker Compose, Tailscale, manual management

Phase 2: Single Cloud VM (1–2 weeks)
  └─ Oracle Cloud or DigitalOcean VM, Terraform-provisioned, Docker Compose

Phase 3: k3s Single-Node (1 month)
  └─ Convert Docker Compose → Helm charts, deploy to k3s on one VM

Phase 4: k3s Multi-Node HA (3–6 months)
  └─ 3-node k3s cluster (1 server, 2 agents), Longhorn storage, MetalLB load balancer
```

---

## Phase 2: Single Cloud VM Migration

### Option A: Oracle Cloud (Free Forever)

#### Prerequisites
- Oracle Cloud account (free tier: https://www.oracle.com/cloud/free/)
- SSH key pair (`ssh-keygen -t ed25519`)
- Terraform installed locally

#### Terraform Setup for Oracle Cloud

```hcl
# terraform/oracle-cloud/provider.tf
terraform {
  required_version = "~> 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}
```

```hcl
# terraform/oracle-cloud/variables.tf
variable "tenancy_ocid" {
  description = "OCI tenancy OCID (from Console > Profile > Tenancy)"
  type        = string
}

variable "user_ocid" {
  description = "OCI user OCID"
  type        = string
}

variable "fingerprint" {
  description = "API key fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to OCI API private key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "OCI region (e.g., us-ashburn-1)"
  type        = string
  default     = "us-ashburn-1"
}

variable "compartment_id" {
  description = "OCI compartment OCID (root or custom)"
  type        = string
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
}
```

```hcl
# terraform/oracle-cloud/main.tf
data "oci_identity_availability_domain" "ad" {
  compartment_id = var.tenancy_ocid
  ad_number      = 1
}

# Always-free ARM VM (4 cores, 24GB RAM)
resource "oci_core_instance" "netdevops_vm" {
  availability_domain = data.oci_identity_availability_domain.ad.name
  compartment_id      = var.compartment_id
  display_name        = "netdevops-stack"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = var.ubuntu_arm_image_id  # Ubuntu 22.04 ARM
  }

  create_vnic_details {
    assign_public_ip = true
    subnet_id        = oci_core_subnet.netdevops_subnet.id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      netbox_token   = var.netbox_token
      influx_token   = var.influx_token
      grafana_password = var.grafana_password
    }))
  }
}

# Networking
resource "oci_core_vcn" "netdevops_vcn" {
  compartment_id = var.compartment_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "netdevops-vcn"
  dns_label      = "netdevops"
}

resource "oci_core_subnet" "netdevops_subnet" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.netdevops_vcn.id
  cidr_block     = "10.0.1.0/24"
  display_name   = "netdevops-subnet"
  dns_label      = "apps"
}

resource "oci_core_internet_gateway" "netdevops_igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.netdevops_vcn.id
  display_name   = "netdevops-igw"
}

resource "oci_core_route_table" "netdevops_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.netdevops_vcn.id
  display_name   = "netdevops-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.netdevops_igw.id
  }
}

# Security: Allow Grafana, InfluxDB, NetBox, SSH
resource "oci_core_security_list" "netdevops_seclist" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.netdevops_vcn.id
  display_name   = "netdevops-seclist"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"  # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 3000
      max = 3000
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 8086
      max = 8086
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 8000
      max = 8000
    }
  }
}

# Outputs
output "vm_public_ip" {
  value       = oci_core_instance.netdevops_vm.public_ip
  description = "Public IP of NetDevOps VM"
}

output "ssh_command" {
  value       = "ssh ubuntu@${oci_core_instance.netdevops_vm.public_ip}"
  description = "SSH access command"
}
```

```yaml
# terraform/oracle-cloud/cloud-init.yaml
#cloud-config
packages:
  - docker.io
  - docker-compose
  - git
  - curl

runcmd:
  - systemctl enable docker
  - systemctl start docker
  - usermod -aG docker ubuntu
  - git clone https://github.com/YOUR_USERNAME/netdevops-project2.git /home/ubuntu/netdevops-project2
  - chown -R ubuntu:ubuntu /home/ubuntu/netdevops-project2
  - cd /home/ubuntu/netdevops-project2 && echo "NETBOX_API_TOKEN=${netbox_token}" >> .env
  - cd /home/ubuntu/netdevops-project2 && echo "INFLUXDB_TOKEN=${influx_token}" >> .env
  - cd /home/ubuntu/netdevops-project2 && echo "GRAFANA_ADMIN_PASSWORD=${grafana_password}" >> .env
  - cd /home/ubuntu/netdevops-project2 && docker compose up -d
```

#### Deploy Oracle Cloud VM

```bash
cd terraform/oracle-cloud

# Create terraform.tfvars (gitignored)
cat > terraform.tfvars <<EOF
tenancy_ocid      = "ocid1.tenancy.oc1..aaaaaaaa..."
user_ocid         = "ocid1.user.oc1..aaaaaaaa..."
fingerprint       = "aa:bb:cc:dd:..."
compartment_id    = "ocid1.compartment.oc1..aaaaaaaa..."
ssh_public_key    = "$(cat ~/.ssh/id_ed25519.pub)"
ubuntu_arm_image_id = "ocid1.image.oc1.iad.aaaaaaaa..."  # Find in Console > Compute > Images
netbox_token      = "your-netbox-token"
influx_token      = "your-influx-token"
grafana_password  = "your-grafana-password"
EOF

terraform init
terraform plan
terraform apply
```

**Cost:** $0/month (forever free tier).

---

### Option B: DigitalOcean

#### Terraform Setup for DigitalOcean

```hcl
# terraform/digitalocean/provider.tf
terraform {
  required_version = "~> 1.5"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}
```

```hcl
# terraform/digitalocean/main.tf
resource "digitalocean_droplet" "netdevops" {
  image  = "ubuntu-22-04-x64"
  name   = "netdevops-stack"
  region = "nyc3"
  size   = "s-2vcpu-4gb"  # $24/month
  ssh_keys = [digitalocean_ssh_key.default.id]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    netbox_token     = var.netbox_token
    influx_token     = var.influx_token
    grafana_password = var.grafana_password
  })
}

resource "digitalocean_ssh_key" "default" {
  name       = "netdevops-key"
  public_key = var.ssh_public_key
}

resource "digitalocean_firewall" "netdevops" {
  name = "netdevops-firewall"

  droplet_ids = [digitalocean_droplet.netdevops.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "3000"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8086"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8000"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

output "droplet_ip" {
  value       = digitalocean_droplet.netdevops.ipv4_address
  description = "Public IP of NetDevOps droplet"
}
```

#### Deploy DigitalOcean Droplet

```bash
cd terraform/digitalocean

# Get DO API token from: https://cloud.digitalocean.com/account/api/tokens
export TF_VAR_do_token="dop_v1_xxxxxxx"

cat > terraform.tfvars <<EOF
ssh_public_key   = "$(cat ~/.ssh/id_ed25519.pub)"
netbox_token     = "your-netbox-token"
influx_token     = "your-influx-token"
grafana_password = "your-grafana-password"
EOF

terraform init
terraform plan
terraform apply
```

**Cost:** $24/month (2 vCPU, 4GB RAM).

---

## Phase 3: k3s Single-Node Migration

### Why k3s for NetDevOps?

**Perfect Fit Because:**
- Monitoring workloads are stateful but not massively scalable (NetBox DB, InfluxDB writes).
- You need container orchestration (auto-restart, health checks, declarative config) but not cloud-provider integrations.
- Single-node k3s on Oracle Cloud free tier = production-grade orchestration at $0/month.

### Install k3s on Cloud VM

```bash
# SSH into Oracle Cloud or DigitalOcean VM
ssh ubuntu@<VM_IP>

# Install k3s (single-node, embedded SQLite)
curl -sfL https://get.k3s.io | sh -

# Verify cluster
sudo kubectl get nodes
# NAME              STATUS   ROLES                  AGE   VERSION
# netdevops-stack   Ready    control-plane,master   30s   v1.28.2+k3s1

# Get kubeconfig for local access
sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/config
sed -i "s/127.0.0.1/<VM_PUBLIC_IP>/g" ~/.kube/config
chmod 600 ~/.kube/config

# From your laptop:
export KUBECONFIG=~/.kube/netdevops-k3s.yaml
kubectl get nodes
```

### Convert Docker Compose → Kubernetes Manifests

**InfluxDB Deployment:**

```yaml
# k3s/influxdb-deployment.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: influxdb-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: influxdb
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: influxdb
  template:
    metadata:
      labels:
        app: influxdb
    spec:
      containers:
      - name: influxdb
        image: influxdb:2.7.10
        ports:
        - containerPort: 8086
        env:
        - name: DOCKER_INFLUXDB_INIT_MODE
          value: "setup"
        - name: DOCKER_INFLUXDB_INIT_USERNAME
          valueFrom:
            secretKeyRef:
              name: influxdb-secret
              key: username
        - name: DOCKER_INFLUXDB_INIT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: influxdb-secret
              key: password
        - name: DOCKER_INFLUXDB_INIT_ORG
          value: "netdevops"
        - name: DOCKER_INFLUXDB_INIT_BUCKET
          value: "network_health"
        volumeMounts:
        - name: influxdb-storage
          mountPath: /var/lib/influxdb2
      volumes:
      - name: influxdb-storage
        persistentVolumeClaim:
          claimName: influxdb-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: influxdb
  namespace: monitoring
spec:
  selector:
    app: influxdb
  ports:
  - port: 8086
    targetPort: 8086
  type: LoadBalancer  # k3s uses Traefik for LB
```

**Grafana Deployment:**

```yaml
# k3s/grafana-deployment.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.4.3
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-secret
              key: password
        - name: INFLUX_URL
          value: "http://influxdb.monitoring.svc.cluster.local:8086"
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        - name: grafana-dashboards
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: grafana-storage
        persistentVolumeClaim:
          claimName: grafana-pvc
      - name: grafana-dashboards
        configMap:
          name: grafana-dashboards
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
  type: LoadBalancer
```

**Poller CronJob:**

```yaml
# k3s/poller-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: health-poller
  namespace: monitoring
spec:
  schedule: "*/1 * * * *"  # Every minute
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: poller
            image: python:3.12-slim
            command:
            - /bin/bash
            - -c
            - |
              pip install pynetbox icmplib influxdb-client python-dotenv
              python /app/health_poller.py --once
            env:
            - name: NETBOX_API_URL
              value: "http://netbox.netdevops.svc.cluster.local:8000"
            - name: NETBOX_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: netbox-secret
                  key: token
            - name: INFLUXDB_URL
              value: "http://influxdb.monitoring.svc.cluster.local:8086"
            - name: INFLUXDB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: influxdb-secret
                  key: token
            volumeMounts:
            - name: poller-script
              mountPath: /app
          volumes:
          - name: poller-script
            configMap:
              name: poller-script
          restartPolicy: OnFailure
```

### Deploy to k3s

```bash
# Create namespace
kubectl create namespace monitoring

# Create secrets
kubectl create secret generic influxdb-secret \
  --from-literal=username=admin \
  --from-literal=password=your-password \
  --from-literal=token=your-token \
  -n monitoring

kubectl create secret generic grafana-secret \
  --from-literal=password=your-grafana-password \
  -n monitoring

# Deploy apps
kubectl apply -f k3s/influxdb-deployment.yaml
kubectl apply -f k3s/grafana-deployment.yaml
kubectl apply -f k3s/poller-cronjob.yaml

# Check status
kubectl get pods -n monitoring
kubectl get svc -n monitoring

# Access Grafana (get LoadBalancer IP)
kubectl get svc grafana -n monitoring
# NAME      TYPE           CLUSTER-IP      EXTERNAL-IP       PORT(S)
# grafana   LoadBalancer   10.43.100.123   <VM_PUBLIC_IP>   3000:30123/TCP
```

---

## Phase 4: k3s Multi-Node HA (Optional Future)

### When to Scale

- Monitoring 100+ devices.
- Need zero-downtime upgrades.
- Want node failure tolerance.

### Architecture

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  k3s Server      │  │  k3s Agent 1     │  │  k3s Agent 2     │
│  (Control Plane) │  │  (Worker)        │  │  (Worker)        │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ - etcd           │  │ - InfluxDB pod   │  │ - Grafana pod x2 │
│ - API Server     │  │ - NetBox pod     │  │ - Poller CronJob │
│ - Scheduler      │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                   k3s Internal Network
```

**Setup:**
```bash
# Server node
curl -sfL https://get.k3s.io | sh -s - server \
  --cluster-init \
  --tls-san <VM_PUBLIC_IP>

# Agent nodes (get token from /var/lib/rancher/k3s/server/node-token)
curl -sfL https://get.k3s.io | K3S_URL=https://<SERVER_IP>:6443 \
  K3S_TOKEN=<NODE_TOKEN> sh -
```

**Cost:** 3x Oracle Cloud free VMs = $0/month or 3x DO droplets = $18–$72/month.

---

## Migration Checklist

### Pre-Migration
- [ ] Backup NetBox database (`docker exec -t project1-postgres pg_dump > netbox_backup.sql`)
- [ ] Backup InfluxDB (`influx backup /tmp/influxdb_backup`)
- [ ] Export Grafana dashboards (API or UI export)
- [ ] Document current `.env` variables

### Phase 2 (Cloud VM)
- [ ] Choose provider (Oracle Cloud free or DigitalOcean)
- [ ] Create Terraform config (use templates above)
- [ ] Run `terraform apply`
- [ ] SSH to VM and verify Docker containers running
- [ ] Update DNS or Tailscale to point to new IP
- [ ] Restore NetBox/InfluxDB data
- [ ] Test Grafana dashboards

### Phase 3 (k3s)
- [ ] Install k3s on cloud VM
- [ ] Convert docker-compose to k8s manifests
- [ ] Create secrets (`kubectl create secret`)
- [ ] Deploy apps (`kubectl apply -f k3s/`)
- [ ] Verify pods running (`kubectl get pods -n monitoring`)
- [ ] Access via LoadBalancer IPs

### Post-Migration
- [ ] Update README with new URLs
- [ ] Update CHANGELOG with migration date
- [ ] Decommission laptop VM (or keep as dev environment)
- [ ] Set up monitoring for k3s cluster (Prometheus + Grafana)

---

## Cost Comparison

| Option | Setup | Monthly Cost | Pros | Cons |
|--------|-------|--------------|------|------|
| **Laptop VM** | Manual | $0 (electricity) | Full control, offline-capable | Laptop dependency, no public access |
| **Oracle Cloud** | Terraform | $0 (free tier) | Always-on, public IP, 4 cores | Limited to 1 region, support is basic |
| **DigitalOcean** | Terraform | $6–$24 | Reliable, great docs, snapshots | Monthly cost, lower free tier |
| **k3s on Oracle** | Terraform + kubectl | $0 | Orchestration + free | Learning curve for k8s |
| **k3s on DO** | Terraform + kubectl | $24–$72 | Production-ready HA | Higher cost for multi-node |

---

## Rollback Plan

If migration fails, revert to laptop VM:

```bash
# On laptop VM
cd ~/netdevops-project2
docker compose up -d

# Restore NetBox backup
docker exec -i project1-postgres psql -U netbox < netbox_backup.sql

# Restore InfluxDB backup
docker exec -it project2-influxdb influx restore /tmp/influxdb_backup
```

Keep laptop VM intact until cloud deployment is stable for 2+ weeks.

---

## Next Steps

1. **Complete Terraform Sprints 0–6** (TERRAFORM_PLAN.md)
2. **Choose provider:** Oracle Cloud (free) or DigitalOcean (paid)
3. **Phase 2 migration:** Single VM with Docker Compose
4. **Monitor for 2 weeks**, then proceed to Phase 3 (k3s) if needed

---

## References

- **Oracle Cloud Free Tier**: https://www.oracle.com/cloud/free/
- **DigitalOcean Pricing**: https://www.digitalocean.com/pricing
- **k3s Documentation**: https://docs.k3s.io
- **k3s vs k8s Comparison**: https://k3s.io/#why-k3s
- **Rancher (k3s creator)**: https://www.rancher.com/products/k3s

---

**Last Updated:** 2026-01-17  
**Status:** Ready for Phase 2 (cloud VM migration)  
**Recommended Path:** Oracle Cloud free tier → k3s single-node → (optional) k3s HA
