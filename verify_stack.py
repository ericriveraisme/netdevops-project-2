import subprocess

def check_docker_status(container_name):
    """Check if a specific Docker container is running, suppressing template errors."""
    # First, just check if it's running. This works for ALL containers.
    cmd = f"docker inspect --format='{{{{.State.Running}}}}' {container_name} 2>/dev/null"
    try:
        is_running = subprocess.check_output(cmd, shell=True).decode().strip() == "true"
        if not is_running:
            return False
            
        # Optional: Check for 'healthy' status if the container supports it
        health_cmd = f"docker inspect --format='{{{{.State.Health.Status}}}}' {container_name} 2>/dev/null"
        try:
            health_status = subprocess.check_output(health_cmd, shell=True).decode().strip()
            # If it has a health check, return True only if it's healthy or starting
            return health_status in ["healthy", "starting"]
        except:
            # If no health check exists, being 'running' is enough
            return True
    except:
        return False

def check_systemd_status(service_name):
    """Check if a systemd service is active."""
    cmd = f"systemctl is-active {service_name}"
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip() == "active"
    except:
        return False

def run_verification():
    print("🔍 --- Project 2 Stack Verification --- 🔍")
    
    netbox_containers = ["netbox-docker-netbox-1", "netbox-docker-postgres-1", "netbox-docker-redis-1"]
    print("\n[Project 1: NetBox Stack]")
    for c in netbox_containers:
        print(f"  {c:30} {'✅ UP' if check_docker_status(c) else '❌ DOWN'}")

    monitoring_containers = ["project2-influxdb", "project2-grafana"]
    print("\n[Project 2: Monitoring Stack]")
    for c in monitoring_containers:
        print(f"  {c:30} {'✅ UP' if check_docker_status(c) else '❌ DOWN'}")

    print("\n[Linux Services]")
    print(f"  {'net-poller.service':30} {'✅ RUNNING' if check_systemd_status('net-poller') else '❌ FAILED'}")

    print("\n" + "="*40)
    # Final logical check
    if check_systemd_status("net-poller") and check_docker_status("project2-influxdb"):
        print("🚀 SYSTEM STATUS: ALL SYSTEMS GO")
    else:
        print("⚠️ SYSTEM STATUS: ATTENTION REQUIRED")

if __name__ == "__main__":
    run_verification()