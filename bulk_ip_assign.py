import logging
import os
from typing import Optional

import pynetbox
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
nb = pynetbox.api(url=os.getenv("NETBOX_URL"), token=os.getenv("NETBOX_TOKEN"))

def bulk_assign_ips(device_name: str, ip_str: str) -> Optional[str]:
    device = nb.dcim.devices.get(name=device_name)
    if not device:
        logging.error("Device %s not found in NetBox.", device_name)
        return None

    interface = nb.dcim.interfaces.get(device_id=device.id, name='Management')
    if not interface:
        interface = nb.dcim.interfaces.create(
            device=device.id,
            name='Management',
            type='virtual'
        )

    ip_obj = nb.ipam.ip_addresses.get(address=ip_str)
    if not ip_obj:
        ip_obj = nb.ipam.ip_addresses.create(
            address=ip_str,
            assigned_object_type='dcim.interface',
            assigned_object_id=interface.id
        )

    device.update({'primary_ip4': ip_obj.id})
    logging.info("Successfully configured %s with Primary IP %s", device_name, ip_str)
    return ip_str

# Example Usage:
# bulk_assign_ips('EDGE-ROUTER-01', '100.89.136.1/32')
