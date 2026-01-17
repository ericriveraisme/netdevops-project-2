import os
from dotenv import load_dotenv
import pynetbox

load_dotenv()
nb = pynetbox.api(url=os.getenv('NETBOX_URL'), token=os.getenv('NETBOX_TOKEN'))

def bulk_assign_ips(device_name, ip_str):
    device = nb.dcim.devices.get(name=device_name)
    
    # 1. Create the Interface
    interface = nb.dcim.interfaces.create(
        device=device.id,
        name='Management',
        type='virtual'
    )
    
    # 2. Create and Assign the IP
    ip_obj = nb.ipam.ip_addresses.create(
        address=ip_str,
        assigned_object_type='dcim.interface',
        assigned_object_id=interface.id
    )
    
    # 3. Set as Primary
    device.update({'primary_ip4': ip_obj.id})
    print(f"✅ Successfully configured {device_name} with Primary IP {ip_str}")

# Example Usage:
# bulk_assign_ips('EDGE-ROUTER-01', '100.89.136.1/32')
