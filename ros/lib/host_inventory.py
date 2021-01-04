import requests
from ros.config import INVENTORY_ADDRESS


def fetch_host_from_inventory(insights_id, rh_identity):
    host_api_url = f"{INVENTORY_ADDRESS}/api/inventory/v1/hosts?insights_id={insights_id}"
    headers = {'x-rh-identity': rh_identity, 'Content-Type': 'application/json'}
    res = requests.get(host_api_url, headers=headers)
    hosts = res.json()
    return hosts
