import os
from dotenv import load_dotenv
import pynetbox

load_dotenv()
nb = pynetbox.api(url=os.getenv('NETBOX_URL'), token=os.getenv('NETBOX_TOKEN'))

def discover_inventory_slugs():
    print("--- 🏛️ REQUIRED SLUGS FOR YOUR SCRIPT ---")
    
    print("\n[Device Roles]")
    for role in nb.dcim.device_roles.all():
        print(f"  - Name: {role.name:20} | Slug: {role.slug}")

    print("\n[Device Types / Models]")
    for d_type in nb.dcim.device_types.all():
        print(f"  - Name: {d_type.model:20} | Slug: {d_type.slug}")

    print("\n[Sites]")
    # FIXED: removed the extra .nb
    for site in nb.dcim.sites.all():
        print(f"  - Name: {site.name:20} | Slug: {site.slug}")

if __name__ == "__main__":
    discover_inventory_slugs()