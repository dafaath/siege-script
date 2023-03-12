#!/usr/bin/env python3
"""_summary_: Clean the result of run.sh script and generate a summary file"""

import json
# import logging
from pathlib import Path
from typing import Dict, List
import pytz
import re
from datetime import datetime
import os
import pandas as pd
import sys

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(THIS_FOLDER, "summary")
RESULT_FOLDER = os.path.join(THIS_FOLDER, "result")

# logging.basicConfig(
#     format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
# )


def convert_data_frames_to_excel(data_frames: Dict[str, pd.DataFrame], writer: pd.ExcelWriter):
    for (
        sheetname,
        data_frame,
    ) in data_frames.items():  # loop through `dict` of dataframes
        data_frame.to_excel(writer, sheet_name=sheetname)  # send data_frame to writer
        worksheet = writer.sheets[sheetname]  # pull worksheet object
        for idx, col in enumerate(data_frame):  # loop through all columns
            series = data_frame[col]
            max_len = (
                max(
                    (
                        series.astype(str).map(len).max(),  # len of largest item
                        len(str(series.name)),  # len of column name/header
                    )
                )
                + 1
            )  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)  # set column widt


def get_summary(input_file_name):
    input_file = open(input_file_name, "r")
    filename_without_ext = Path(input_file_name).with_suffix("").name
    print(f"Processing {filename_without_ext}")
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
                "server": filename_without_ext,
                "time": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "epoch": epoch_timestamp,
                "endpoint": f"{method} {path}",
                "concurrent": concurrency,
                "iteration": iteration,
                **siege_data,
            }
            output_data.append(data)
        elif line.startswith("Sleeping"):
            continue

    print(f"Constructing dataframe from {filename_without_ext}")

    df = pd.DataFrame(output_data)
    df_group_by_concurrent = df.groupby(
        ["server", "endpoint", "concurrent"], dropna=False
    ).mean(numeric_only=True)
    df_group_by_endpoint = df.groupby(["server", "endpoint"], dropna=False).mean(
        numeric_only=True
    )
    df_group_by_server = df.groupby(["server"], dropna=False).mean(numeric_only=True)

    output_filename = f"{OUTPUT_FOLDER}/summary_{filename_without_ext}.xlsx"
    writer = pd.ExcelWriter(output_filename, engine="xlsxwriter")

    data_frames = {
        "All": df,
        "Group By Concurrent": df_group_by_concurrent,
        "Group By Endpoint": df_group_by_endpoint,
        "Group By Server": df_group_by_server,
    }
    convert_data_frames_to_excel(data_frames, writer)

    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
    input_file.close()

    print(f"Finish processing {filename_without_ext}")
    print(f"Output to {OUTPUT_FOLDER}/summary_{filename_without_ext}.xlsx")

    return df


def combine_summary(data_frames: List[pd.DataFrame]):
    print("Combine all summary")
    df = pd.concat(data_frames)

    df_group_by_concurrent = df.groupby(
        ["server", "endpoint", "concurrent"], dropna=False
    ).mean(numeric_only=True)
    df_group_by_endpoint = df.groupby(["server", "endpoint"], dropna=False).mean(
        numeric_only=True
    )
    df_group_by_server = df.groupby(["server"], dropna=False).mean(numeric_only=True)

    output_filename = f"{OUTPUT_FOLDER}/summary_all.xlsx"
    writer = pd.ExcelWriter(output_filename, engine="xlsxwriter")

    # Write each dataframe to a different worksheet.
    dfs = {
        "All": df,
        "Group By Concurrent": df_group_by_concurrent,
        "Group By Endpoint": df_group_by_endpoint,
        "Group By Server": df_group_by_server,
    }
    convert_data_frames_to_excel(dfs, writer)

    print(f"Output to {output_filename}")

    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
    print("Finish Combine all summary")


def main():
    args = sys.argv
    if len(args) < 2:
        print(
            """Usage: python get_summary.py [<filename>|all]
example: get_summary.py result_dafav1.txt
or 'python get_summary.py all' to get all summary"""
        )
        sys.exit(1)

    data_frames: List[pd.DataFrame] = []
    if args[1] == "all":
        for file in os.listdir(RESULT_FOLDER):
            full_path = os.path.join(RESULT_FOLDER, file)
            df = get_summary(full_path)
            data_frames.append(df)

        combine_summary(data_frames)
    else:
        get_summary(args[1])


if __name__ == "__main__":
    main()
