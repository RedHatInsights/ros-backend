import json
from os import path

root = path.dirname(path.realpath(__file__)).split('telemetry')[0]


def load_json(file_path):
    """
    Function to load JSON file
    """
    try:
        with open(file_path) as fp:
            return json.load(fp)
    except Exception as e:
        raise Exception(e)


def one_or_more(items=None):
    items = [] if items is None else items
    if isinstance(items, str):
        items = [items]
    elif isinstance(items, (list, tuple, set)):
        items = list(set(items))
    else:
        raise Exception("Only a string or list of strings can be query")
    return items


class Ec2LinuxPrices(dict):
    """
    Pricing information of EC2 Instance.
    - https://raw.githubusercontent.com/apache/libcloud/trunk/contrib/scrape-ec2-prices.py
    """
    def __init__(self, json_files='ec2_instance_pricing.json'):
        super(Ec2LinuxPrices, self).__init__()

        for jf in one_or_more(json_files):
            self.update(load_json(path.join(root, jf)).get('compute').get('ec2_linux'))
