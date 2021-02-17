import requests
from .config import INVENTORY_URL


def fetch_host_from_inventory(insights_id, rh_identity):
    host_api_url = f"{INVENTORY_URL}/api/inventory/v1/hosts?insights_id={insights_id}"
    headers = {'x-rh-identity': rh_identity, 'Content-Type': 'application/json'}
    res = requests.get(host_api_url, headers=headers)
    hosts = res.json()
    return hosts


def fetch_all_hosts_from_inventory(rh_identity):
    hosts_api_url = f"{INVENTORY_URL}/api/inventory/v1/hosts"
    headers = {'x-rh-identity': rh_identity, 'Content-Type': 'application/json'}
    response = requests.get(hosts_api_url, headers=headers)
    hosts_list = response.json()
    return hosts_list
