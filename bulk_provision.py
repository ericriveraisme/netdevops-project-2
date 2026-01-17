import os
from dotenv import load_dotenv
import pynetbox

load_dotenv()
nb = pynetbox.api(url=os.getenv('NETBOX_URL'), token=os.getenv('NETBOX_TOKEN'))

# UPDATED: These now match your get_slugs.py output exactly
new_devices = [
    {
        'name': 'EDGE-ROUTER-02', 
        'role': 'edge-router', 
        'model': 'generic-switch', # Using the slug we know exists
        'site': 'main-office', 
        'ip': '100.89.136.2/32'
    },
    {
        'name': 'DIST-SW-03', 
        'role': 'distribution-switch', 
        'model': 'generic-switch', 
        'site': 'remote-branch', 
        'ip': '100.89.136.3/32'
    }
]

def provision_device_idempotent(data):
    # 1. VALIDATION: Check if slugs exist
    role = nb.dcim.device_roles.get(slug=data['role'])
    d_type = nb.dcim.device_types.get(slug=data['model'])
    site = nb.dcim.sites.get(slug=data['site'])

    if not all([role, d_type, site]):
        missing = [k for k, v in {'role': role, 'model': d_type, 'site': site}.items() if not v]
        raise ValueError(f"Missing slugs in NetBox: {missing}")

    # 2. IDEMPOTENCY: Check if device exists
    device = nb.dcim.devices.get(name=data['name'])
    if device:
        print(f"ℹ️ {data['name']} already exists. Skipping creation.")
    else:
        print(f"🚀 Creating {data['name']}...")
        device = nb.dcim.devices.create(
            name=data['name'],
            device_type=d_type.id,
            role=role.id,
            site=site.id,
            status='active'
        )

    # 3. INTERFACE: Ensure 'Management' interface exists
    interface = nb.dcim.interfaces.get(device_id=device.id, name='Management')
    if not interface:
        interface = nb.dcim.interfaces.create(
            device=device.id,
            name='Management',
            type='virtual'
        )

    # 4. IP ADDRESS: Ensure IP exists and is linked
    ip_addr = nb.ipam.ip_addresses.get(address=data['ip'])
    if not ip_addr:
        ip_addr = nb.ipam.ip_addresses.create(
            address=data['ip'],
            assigned_object_type='dcim.interface',
            assigned_object_id=interface.id,
            status='active'
        )
    
    # 5. SET PRIMARY: Ensure the pointer is correct
    if not device.primary_ip4 or device.primary_ip4.id != ip_addr.id:
        device.update({'primary_ip4': ip_addr.id})
        print(f"✅ {data['name']} is now live and set as primary.")
    else:
        print(f"✅ {data['name']} configuration is already correct.")

if __name__ == "__main__":
    for entry in new_devices:
        try:
            provision_device_idempotent(entry)
        except Exception as e:
            print(f"❌ Error provisioning {entry['name']}: {e}")