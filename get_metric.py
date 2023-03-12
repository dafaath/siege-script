#!/usr/bin/env python3

"""
Script to get metrics from Digital Ocean API.
The output is a JSON file in the metric folder with the following format:
<output_name>_<metric_name>_<start>_<end>.json
"""

from datetime import datetime
import json
from typing import Dict, List, Optional
import requests
import sys
import os
import pandas as pd
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
METRICS_TO_GET = [
    "cpu",
    "memory_free",
    "memory_available",
    "memory_total",
    "load_15",
    "load_5",
    "load_1",
]

BASE_SERVER_HOST_ID = {
    "dafa": "343177628",
    "alvin": "344294881",
    "hanin": "343280614",
}


def get_start_and_end_from_server_data(server_data):
    server_data.sort_values(by=["epoch"])
    start = server_data.iloc[0]["epoch"]
    end = server_data.iloc[-1]["epoch"]
    return start, end


def get_server_host_id(server_name):
    for base_server in BASE_SERVER_HOST_ID:
        if base_server in server_name:
            return BASE_SERVER_HOST_ID[base_server]

    return None


def get_metric_from_summary_file(summary_file_name):
    df = pd.read_excel(summary_file_name, sheet_name="All")
    server_metric_data: Dict[str, Optional[Dict[str, str]]] = {}
    server_names = df["server"].unique()
    for server_name in server_names:
        df_server = df.loc[df["server"] == server_name]
        start, end = get_start_and_end_from_server_data(df_server)
        host_id = get_server_host_id(server_name)

        if host_id is None:
            server_metric_data[server_name] = None
            print(f"Cannot find host_id for {server_name}")
            continue

        server_metric_data[server_name] = {
            "host_id": host_id,
            "start": start,
            "end": end,
        }

    metric_dataframes: List[pd.DataFrame] = []
    for server_name, server_metric in server_metric_data.items():
        if server_metric is not None:
            metric_df = get_metric(
                server_metric["host_id"],
                server_metric["start"],
                server_metric["end"],
                server_name,
            )
            metric_dataframes.append(metric_df)
        else:
            print(f"Cannot find host_id for {server_name}")

    return pd.concat(metric_dataframes)


def get_metric(host_id, start, end, output_name):
    all_metric_data = {}

    for metric in METRICS_TO_GET:
        output_filename = os.path.join(
            OUTPUT_FOLDER, f"{output_name}_{metric}_{start}_{end}.json"
        )

        if os.path.exists(output_filename):
            print(f"Using cached file {output_filename}")
            json_response = json.load(open(output_filename))
        else:
            url = f"{DIGITAL_OCEAN_BASE_URL_API}/{metric}"
            params = {"host_id": host_id, "start": start, "end": end}
            header = {"Authorization": f"Bearer {DIGITAL_OCEAN_API_KEY}"}
            response = requests.get(url, params=params, headers=header)
            json_response = response.json()
            with open(output_filename, "w") as output_file:
                output_file.write(json.dumps(json_response, indent=2))
                print(f"Output written to {output_file.name}")

        result = json_response["data"]["result"]
        for res in result:
            mode = ""
            if "mode" in res["metric"]:
                mode = "-" + res["metric"]["mode"]

            values = res["values"]
            for v in values:
                if v[0] not in all_metric_data:
                    all_metric_data[v[0]] = {
                        f"{metric}{mode}": float(v[1]),
                    }
                else:
                    all_metric_data[v[0]] = {
                        f"{metric}{mode}": float(v[1]),
                        **all_metric_data[v[0]],
                    }

    all_metric_data_matrix = []
    for time in all_metric_data:
        all_metric_data_matrix.append(
            {
                "server": output_name,
                "epoch": time,
                "time": datetime.fromtimestamp(time).strftime("%Y-%m-%d %H:%M:%S %Z"),
                **all_metric_data[time],
            }
        )

    df = pd.DataFrame(all_metric_data_matrix)
    return df


def main():
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

    df = get_metric(args[1], args[2], args[3], args[4])
    df.to_csv(f"{OUTPUT_FOLDER}/{args[4]}.csv", index=False)


if __name__ == "__main__":
    main()
