import argparse
import functools
import logging
import os
import random
import signal
import sys
import time
from typing import Optional

import pynetbox
import requests
from dotenv import load_dotenv
from icmplib import ping
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        logging.error("Missing required environment variable %s", key)
        sys.exit(1)
    return value


def build_netbox_client() -> pynetbox.api:
    nb = pynetbox.api(url=require_env("NETBOX_URL"), token=require_env("NETBOX_TOKEN"))
    session = requests.Session()
    # Apply a default timeout to all NetBox requests.
    session.request = functools.partial(session.request, timeout=5)  # type: ignore[assignment]
    nb.http_session = session
    return nb


def build_influx_client() -> InfluxDBClient:
    return InfluxDBClient(
        url=require_env("INFLUX_URL"),
        token=require_env("INFLUX_TOKEN"),
        org=require_env("INFLUX_ORG"),
    )


def build_point(device_name: str, site: str, status: int, latency_ms: float) -> Point:
    return (
        Point("device_health")
        .tag("device_name", device_name)
        .tag("site", site)
        .field("status", status)
        .field("latency", latency_ms)
    )

def poll_network(nb: pynetbox.api, write_api) -> None:
    # Fetch all active devices from NetBox
    try:
        devices = nb.dcim.devices.filter(status="active")
    except Exception as exc:  # pragma: no cover - depends on external service
        logging.error("Failed to query NetBox devices: %s", exc)
        return
    
    for device in devices:
        # Check if the device has a primary IP assigned
        if device.primary_ip:
            ip_addr = str(device.primary_ip.address).split("/")[0]
            logging.info("Checking %s at %s", device.name, ip_addr)

            try:
                result = ping(ip_addr, count=2, interval=0.2, privileged=False, timeout=2)
            except Exception as exc:  # pragma: no cover - external call
                logging.error("Ping failed for %s (%s): %s", device.name, ip_addr, exc)
                continue

            status = 1 if result.is_alive else 0
            latency = max(result.avg_rtt or 0.0, 0.0)

            point = build_point(device.name, device.site.slug, status, latency)
            try:
                write_api.write(bucket=require_env("INFLUX_BUCKET"), record=point)
            except Exception as exc:  # pragma: no cover - external call
                logging.error("Failed to write point for %s: %s", device.name, exc)
                continue

            logging.info("%s: %s (%.3f ms)", device.name, "UP" if status == 1 else "DOWN", latency)
        else:
            logging.warning("%s has no primary IP. Skipping.", device.name)

def main() -> None:
    parser = argparse.ArgumentParser(description="NetDevOps Health Poller")
    parser.add_argument("--once", action="store_true", help="Run a single poll cycle and exit")
    parser.add_argument("--interval", type=int, default=int(os.getenv("POLL_INTERVAL", "30")), help="Polling interval in seconds")
    args = parser.parse_args()

    nb = build_netbox_client()
    influx_client = build_influx_client()
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)

    stop = False

    def handle_sigint(signum, frame):  # noqa: ANN001
        nonlocal stop
        stop = True
        logging.info("Received shutdown signal; finishing current cycle.")

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    if args.once:
        poll_network(nb, write_api)
        return

    poll_interval = max(args.interval, 5)
    while not stop:
        poll_network(nb, write_api)
        # Add small jitter to avoid bursty scheduling.
        sleep_for = poll_interval + random.uniform(-1.0, 1.0)
        logging.info("Waiting %.1f seconds for next poll...", sleep_for)
        time.sleep(max(sleep_for, 1.0))


if __name__ == "__main__":
    main()
