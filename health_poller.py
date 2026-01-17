import os
import time
from dotenv import load_dotenv
import pynetbox
from icmplib import ping
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

# 1. Connect to the Source of Truth (NetBox)
nb = pynetbox.api(url=os.getenv('NETBOX_URL'), token=os.getenv('NETBOX_TOKEN'))

# 2. Connect to the Time-Series DB (InfluxDB)
influx_client = InfluxDBClient(url=os.getenv('INFLUX_URL'), token=os.getenv('INFLUX_TOKEN'), org=os.getenv('INFLUX_ORG'))
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

def poll_network():
    # Fetch all active devices from NetBox
    devices = nb.dcim.devices.filter(status='active')
    
    for device in devices:
        # Check if the device has a primary IP assigned
        if device.primary_ip:
            ip_addr = str(device.primary_ip.address).split('/')[0]
            print(f"📡 Checking {device.name} at {ip_addr}...")
            
            # Perform the Ping
            result = ping(ip_addr, count=2, interval=0.2, privileged=False)
            
            # Logic: If packet loss is 100%, status is 0 (Down). Otherwise 1 (Up).
            status = 1 if result.is_alive else 0
            latency = result.avg_rtt
            
            # 3. Format the data for InfluxDB (The "Point")
            point = Point("device_health") \
                .tag("device_name", device.name) \
                .tag("site", device.site.slug) \
                .field("status", status) \
                .field("latency", latency)
            
            write_api.write(bucket=os.getenv('INFLUX_BUCKET'), record=point)
            print(f"✅ {device.name}: {'UP' if status == 1 else 'DOWN'} ({latency}ms)")
        else:
            print(f"⚠️ {device.name} has no primary IP. Skipping.")

if __name__ == "__main__":
    while True:
        poll_network()
        print("Waiting 30 seconds for next poll...")
        time.sleep(30)
