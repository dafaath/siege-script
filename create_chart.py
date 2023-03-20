from typing import List
import pandas as pd
import sys
from slugify import slugify

import matplotlib.pyplot as plt
import os
import logging

from get_metric import METRICS_TO_GET, get_metric_from_summary_file

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PLOT_FOLDER = os.path.join(THIS_FOLDER, "plot")

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)

V1_SERVER = [
    "hanin",
    "alvinv1",
    "dafav1",
    "dafav1_optimized",
    #  "dafav1_5_min",
]
V2_SERVER = [
    "alvinv2",
    "dafav2",
    "dafav2_optimized",
    # "dafav2_5_min",
]
SERVER = {
    "v1": V1_SERVER,
    "v2": V2_SERVER,
}


def split_dataframe_per_version(df):
    df_v1 = df[df["server"].isin(V1_SERVER)]
    df_v2 = df[df["server"].isin(V2_SERVER)]
    return {
        "v1": df_v1,
        "v2": df_v2,
    }


def create_chart_metric(input_file):
    df = get_metric_from_summary_file(input_file)
    df["cpu"] = (
        df["cpu-idle"]
        / (
            df["cpu-user"]
            + df["cpu-system"]
            + df["cpu-softirq"]
            + df["cpu-nice"]
            + df["cpu-irq"]
            + df["cpu-iowait"]
        )
        * 100
    )
    df["memory_usage"] = df["memory_total"] - df["memory_available"]
    df["memory_usage_percent"] = df["memory_usage"] / df["memory_total"] * 100
    data_frames = split_dataframe_per_version(df)
    for version in data_frames:
        df_version = data_frames[version]
        df_grouped_by_server = df_version.groupby("server").mean(numeric_only=True)
        servers = df_version["server"].unique()
        # Create a dictionary to store the data
        metrics = METRICS_TO_GET + ["cpu", "memory_usage_percent", "memory_usage"]
        for metric in metrics:
            plt.clf()
            plt.cla()
            logging.info(f"Creating plot for {metric}")

            title = f"{metric} comparison"
            df_grouped_by_server.sort_values(by=["server"])
            ax = df_grouped_by_server[metric].plot(
                kind="bar",
                rot=0,
                title=to_title_case(title),
            )
            modify_ax(ax, title, font_size=14, show_legend=False)

            filename = slugify(f"{version}-{title}") + ".png"
            logging.info(f"Saving {filename}")
            plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def to_title_case(inp: str):
    return inp.replace("_", " ").title()


def modify_ax(ax: plt.Axes, title: str, font_size: int = 7, show_legend=True):
    if show_legend:
        ax.legend(
            loc="upper center",
            title=title,
            bbox_to_anchor=(0.5, 1.175),
            ncol=5,
            fancybox=True,
            shadow=True,
        )

    for container in ax.containers:  # type: ignore
        ax.bar_label(container, label_type="edge", fontsize=font_size, fmt="%.1f")


def create_chart_siege_result(input_file):
    logging.info(f"Creating chart from {input_file}")
    df = pd.read_excel(input_file, sheet_name="All")
    data_frames = split_dataframe_per_version(df)
    column_to_compare = "transaction_rate"

    for version in data_frames:
        df_version = data_frames[version]
        endpoints = df_version["endpoint"].unique()
        for endpoint in endpoints:
            logging.info(f"Creating plot for {endpoint}")
            df_endpoint_separated = df_version.loc[df_version["endpoint"] == endpoint]
            concurrents = df_endpoint_separated["concurrent"].unique()
            data = {"concurrent": concurrents}
            for v1_server_name in SERVER[version]:
                df_v1_server = df_endpoint_separated.loc[
                    df_endpoint_separated["server"] == v1_server_name
                ]
                df_v1_server = df_v1_server.groupby(["concurrent"], dropna=False).mean(
                    numeric_only=True
                )
                data[v1_server_name] = df_v1_server[column_to_compare].tolist()

            new_df = pd.DataFrame(data)

            title = f"{endpoint}"
            ax = new_df.plot(
                kind="bar",
                x="concurrent",
                y=SERVER[version],
                ylabel="Request Per Second",
                rot=0,
                width=0.85,
                figsize=(10, 5),
            )
            modify_ax(ax, title)

            logging.info(f"{version} Saving {title}")
            filename = slugify(f"{version}-{title}") + ".png"
            plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def main():
    args = sys.argv
    if len(args) < 2:
        print(
            """Usage: python create_chart.py filename
filname is an xlsx file generated from get_summary.py script
example: create_chart.py summary/all.xlsx"""
        )
        sys.exit(1)

    create_chart_siege_result(args[1])
    create_chart_metric(args[1])


if __name__ == "__main__":
    main()
