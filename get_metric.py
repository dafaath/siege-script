#!/usr/bin/env python3

"""
Script to get metrics from Digital Ocean API.
The output is a JSON file in the metric folder with the following format:
<output_name>_<metric_name>_<start>_<end>.json
"""

from datetime import datetime
import json
import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(THIS_FOLDER, "metrics")
DIGITAL_OCEAN_BASE_URL_API = (
    "https://api.digitalocean.com/v2/monitoring/metrics/droplet"
)
DIGITAL_OCEAN_API_KEY = os.environ.get("DIGITAL_OCEAN_API_KEY")


# See https://docs.digitalocean.com/reference/api/api-reference/#tag/Monitoring
# for the full detail
METRICS_TO_GET = ["cpu", "memory_free" ,"load_15" ,"load_5" ,"load_1", "filesystem_free"]

args = sys.argv
if len(args) < 5:
    print(
        """Usage: python get_metric.py <droplet_id> <start> <end> <output_name>
<start> and <end> must be in epoch timestamp
example: get_metric.py 343280614 1678134676 1678166510 dafav1"""
    )
    sys.exit(1)

assert args[1].isdigit(), "Droplet ID must be a number"
assert args[2].isdigit(), "Start must be in epoch timestamp"
assert args[3].isdigit(), "End must be in epoch timestamp"

now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
for metric in METRICS_TO_GET:
    url = f"{DIGITAL_OCEAN_BASE_URL_API}/{metric}"
    params = {"host_id": args[1], "start": args[2], "end": args[3]}
    header = {"Authorization": f"Bearer {DIGITAL_OCEAN_API_KEY}"}
    response = requests.get(url, params=params, headers=header)
    json_response = response.json()
    with open(
        f"{OUTPUT_FOLDER}/{args[4]}_{metric}_{args[2]}_{args[3]}.json", "w"
    ) as output_file:
        output_file.write(json.dumps(json_response, indent=2))
        print(f"Output written to {output_file.name}")



