import logging
import os
from typing import Optional

import pynetbox
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
nb = pynetbox.api(url=os.getenv("NETBOX_URL"), token=os.getenv("NETBOX_TOKEN"))

def discover_inventory_slugs(filter_site: Optional[str] = None) -> None:
    logging.info("--- Required Slugs for Scripts ---")

    logging.info("[Device Roles]")
    for role in nb.dcim.device_roles.all():
        logging.info("Name: %-20s | Slug: %s", role.name, role.slug)

    logging.info("[Device Types / Models]")
    for d_type in nb.dcim.device_types.all():
        logging.info("Name: %-20s | Slug: %s", d_type.model, d_type.slug)

    logging.info("[Sites]")
    sites = nb.dcim.sites.filter(slug=filter_site) if filter_site else nb.dcim.sites.all()
    for site in sites:
        logging.info("Name: %-20s | Slug: %s", site.name, site.slug)

if __name__ == "__main__":
    discover_inventory_slugs()