#!/usr/bin/env python3
"""_summary_: Clean the result of run.sh script and generate a summary file"""

import json
import pytz
import re
from datetime import datetime
import os
import pandas as pd
import sys

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(THIS_FOLDER, "summary")

args = sys.argv
if len(args) < 1:
    print(
        """Usage: python clean_result.py <filename>
example: clean_result.py result_dafav1.txt"""
    )
    sys.exit(1)


input_file = open(args[1], "r")
content = input_file.readlines()
output_data = []

for idx, line in enumerate(content):
    line = line.strip()
    if line.startswith("[") and line.endswith("]"):
        timestamp = content[idx - 1]
        # find the timestamp in the format (1626120000)
        epoch_timestamp: str = re.findall(r"\(.*?\)", timestamp)[0].strip("()")
        assert (
            epoch_timestamp.isdigit()
        ), f"Posix timestamp must be a number, currently {epoch_timestamp}"

        time = datetime.fromtimestamp(float(epoch_timestamp)).astimezone(
            pytz.timezone("Asia/Jakarta")
        )
        # find the data in format [ GET /node 200][2]
        information_inside_bracket = re.findall(r"\[.*?\]", line)
        temp = information_inside_bracket[0].strip("[]").strip().split(" ")
        method = temp[0]
        path = temp[1]
        concurrency = temp[2]
        iteration = int(information_inside_bracket[1].strip("[]"))

        # Get the json value from siege
        ## Find line starts with bracket
        start_index = -1
        for j, l in enumerate(content[idx:], idx):
            l = l.strip()
            if l.startswith("{"):
                start_index = j
                break

        json_value = content[start_index : start_index + 13]
        json_value = list(
            map(lambda x: x.strip().replace("\t", "").replace(" ", ""), json_value)
        )
        json_value = "".join(json_value)
        siege_data = json.loads(json_value)
        data = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "method": method,
            "path": path,
            "concurrency": concurrency,
            "iteration": iteration,
            **siege_data,
        }
        output_data.append(data)
        print(data)
    elif line.startswith("Sleeping"):
        continue

pd = pd.DataFrame(output_data)
pd.to_csv(f"{OUTPUT_FOLDER}/summary_{args[1]}.csv", index=False)

input_file.close()
