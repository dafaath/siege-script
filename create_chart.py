import logging
import os
import sys
from typing import Dict, List

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from slugify import slugify

from get_metric import METRICS_TO_GET, get_metric_from_summary_file

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PLOT_FOLDER = os.path.join(THIS_FOLDER, "plot")

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)

# Configuration for managing the chart
COLOR = ["cyan", "orange", "limegreen", "tomato", "purple"]
HATCH = [None, "|||||", "/////", "\\\\\\\\\\", "+++", "---"]

# Exclude some endpoints from the chart
EXCLUDE_ENDPOINT_ALL = ["GET /sensor/1", "GET /sensor"]
ENDPOINT_EXCLUDE_VERSION = {
    "v1": EXCLUDE_ENDPOINT_ALL,
    "v2": EXCLUDE_ENDPOINT_ALL,
    "v3": EXCLUDE_ENDPOINT_ALL + ["POST /node", "PUT /node/1", "POST /channel"],
}

V1_SERVER = [
    "hanin",
    "alvinv1",
    "dafav1",
    "dafav1_optimized",
    #  "dafav1_5_min",
]

V1_SERVER_LABEL: Dict[str, str] = {
    "hanin": "Falcon (Hanin 2021)",
    "alvinv1": "Sanic (Ferdiansyah 2023)",
    "dafav1": "Fiber",
    "dafav1_optimized": "Fiber + Go-json",
}

V2_SERVER = [
    "alvinv1",
    "alvinv2",
    "dafav1_optimized",
    "dafav2",
]

V2_SERVER_LABEL: Dict[str, str] = {
    "alvinv1": "Sanic Iter 1 (Ferdiansyah)",
    "alvinv2": "Sanic Iter 2 (Ferdiansyah)",
    "dafav1_optimized": "Fiber + Go-json Iter 1",
    "dafav2": "Fiber + Go-json Iter 2",
}

V3_SERVER = [
    "dafav2",
    "dafav3",
]

V3_SERVER_LABEL: Dict[str, str] = {
    "dafav2": "Fiber REST API (Iterasi 2)",
    "dafav3": "Fiber Antarmuka Pengguna (Iterasi 3)",
}

SERVER = {
    "v1": V1_SERVER,
    "v2": V2_SERVER,
    "v3": V3_SERVER,
}

LABEL = {
    "v1": V1_SERVER_LABEL,
    "v2": V2_SERVER_LABEL,
    "v3": V3_SERVER_LABEL,
}


def split_dataframe_per_version(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Create a dictionary of dataframe per version

    Args:
        df (pd.DataFrame): _description_

    Returns:
        Dict[str, pd.DataFrame]: _description_
    """
    df_v1 = df[df["server"].isin(V1_SERVER)]
    df_v2 = df[df["server"].isin(V2_SERVER)]
    df_v3 = df[df["server"].isin(V3_SERVER)]
    return {
        "v1": df_v1,
        "v2": df_v2,
        "v3": df_v3,
    }


def create_time_chart(df: pd.DataFrame, version: str):
    """Create time chart for each server

    Args:
        df (pd.DataFrame): pandas dataframe that contains the data to be plotted
        version (str): version of the server
    """
    metrics = ["memory_usage_percent"]
    for metric in metrics:
        logging.info(f"Creating plot for {metric}")

        servers = df["server"].unique()
        title = f"{metric} comparison"
        new_df_data = {}
        for server in servers:
            plt.clf()
            plt.cla()
            server_df: pd.DataFrame = df[df["server"] == server].sort_values(
                by=["epoch"]
            )
            server_df_data = server_df[metric].to_list()
            new_df_data[server] = server_df_data
            min = server_df["epoch"].min()
            max = server_df["epoch"].max()
            xnew = np.linspace(min, max, num=1000, endpoint=True)
            f_cubic = interp1d(server_df["epoch"], server_df[metric], kind="cubic")

            x = xnew
            y = f_cubic(xnew)
            plt.plot(x, y)
            plt.fill_between(x, y)
            # plt.ylim(0, 100)
            # ax = server_df.plot(
            #     # rot=0,
            #     # kind="line",
            #     # title=to_title_case(title),
            #     x=xnew,
            #     # legend=True,
            #     y=f_cubic(xnew),
            #     figsize=(10, 5),
            # )

            filename = slugify(f"{version}-{title}-timechart-{server}") + ".png"
            logging.info(f"Saving {filename}")
            # new_df = pd.DataFrame(new_df_data)
            plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def create_bar_chart(df: pd.DataFrame, version: str):
    """Create bar chart for each server

    Args:
        df (pd.DataFrame): pandas dataframe that contains the data to be plotted
        version (str): version of the server
    """
    df_grouped_by_server = df.groupby("server").mean(numeric_only=True)
    # Create a dictionary to store the data
    metrics = METRICS_TO_GET + [
        "memory_usage_percent",
        "memory_usage",
        "memory_usage_mb",
    ]
    for metric in metrics:
        plt.clf()
        plt.cla()
        logging.info(f"Creating plot for {metric}")

        title = f"{metric} comparison"
        if metric == "memory_usage_percent":
            fmt = "%.2f%%"
            ylim = (0, 50)
            ylabel = "Penggunaan memori (%)"
        elif metric == "memory_usage_mb":
            fmt = "%.1f"
            ylim = (0, 4000)
            ylabel = "Penggunaan memori (mb)"
        else:
            fmt = "%.1f"
            ylim = None
            ylabel = "Penggunaan memori"

        server_labelled = []
        for server in SERVER[version]:
            server_labelled.append(LABEL[version][server])
        df_metric = df_grouped_by_server[metric].reindex(server_labelled)
        ax = df_metric.plot(
            kind="bar",
            rot=0,
            # title=to_title_case(title),
            ylim=ylim,  # type: ignore
            xlabel="Server",
            ylabel=ylabel,
            figsize=(10, 5),
            color=COLOR,
        )
        excel_filename = slugify(f"{version}-{title}") + ".xlsx"
        df_metric.to_excel(os.path.join(PLOT_FOLDER, excel_filename))

        bars = ax.patches
        hatches = [h for h in HATCH for j in range(len(df_metric))]

        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)
        modify_ax(ax, title, font_size=12, show_legend=False, fmt=fmt)

        filename = slugify(f"{version}-{title}") + ".png"
        logging.info(f"Saving {filename}")
        plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def create_chart_metric(input_file):
    """Create chart for each metric in the input file and save it to the PLOT_FOLDER folder

    Args:
        input_file (_type_): xlsx file that contains the data to be plotted
    """
    df = get_metric_from_summary_file(input_file)
    df["memory_usage"] = df["memory_total"] - df["memory_available"]
    df["memory_usage_percent"] = df["memory_usage"] / df["memory_total"] * 100
    df["memory_usage_mb"] = df["memory_usage"] / 1_000_000
    data_frames = split_dataframe_per_version(df)
    for version in data_frames:
        df_version = data_frames[version]
        label_version = LABEL[version]
        for old_label in label_version:
            new_label = label_version[old_label]
            df_version.loc[df_version["server"] == old_label, "server"] = new_label
        create_bar_chart(df_version, version)
        create_time_chart(df_version, version)


def to_title_case(inp: str):
    """Convert input string to title case

    Args:
        inp (str): input string

    Returns:
        _type_: string in title case
    """
    return inp.replace("_", " ").title()


def modify_ax(
    ax: plt.Axes, title: str, font_size: int = 6, show_legend=True, fmt: str = "%.1f"
):
    """Modify the axis of the plot

    Args:
        ax (plt.Axes): axis of the plot
        title (str): title of the plot
        font_size (int, optional): _description_. Defaults to 6.
        show_legend (bool, optional): _description_. Defaults to True.
        fmt (str, optional): _description_. Defaults to "%.1f".
    """
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
        ax.bar_label(container, label_type="edge", fontsize=font_size, fmt=fmt)


def create_chart_per_endpoint(
    endpoint: str, df_version: pd.DataFrame, version: str, column_to_compare: str
):
    logging.info(f"Creating plot for {endpoint}")
    df_endpoint_separated = df_version.loc[df_version["endpoint"] == endpoint]
    concurrents = df_endpoint_separated["concurrent"].unique()
    data = {"concurrent": concurrents}
    for v1_server_name in SERVER[version]:
        df_v1_server = df_endpoint_separated.loc[
            df_endpoint_separated["server"] == v1_server_name
        ]
        df_v1_server = (
            df_v1_server.groupby(["concurrent"], dropna=False)
            .mean(numeric_only=True)
            .sort_values(by=["concurrent"])
        )
        label = LABEL[version][v1_server_name]
        data[label] = df_v1_server[column_to_compare].tolist()

    new_df = pd.DataFrame(data)

    title = f"{endpoint}"
    y_label = [l for l in LABEL[version].values()]
    ax = new_df.plot(
        kind="bar",
        x="concurrent",
        y=y_label,
        ylabel="Transaksi per detik",
        xlabel="Konkurensi",
        rot=0,
        width=0.85,
        figsize=(10, 5),
        color=COLOR,
        # fill=False,
    )
    bars = ax.patches
    hatches = [h for h in HATCH for j in range(len(new_df))]

    excel_filename = slugify(f"{version}-{title}") + ".xlsx"
    new_df.to_excel(os.path.join(PLOT_FOLDER, excel_filename))

    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    modify_ax(ax, title)

    logging.info(f"{version} Saving {title}")
    filename = slugify(f"{version}-{title}") + ".png"
    plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def create_chart_all_endpoint(
    df_version: pd.DataFrame, column_to_compare: str, version: str
):
    endpoints = df_version["endpoint"].unique()
    datas = {"endpoint": endpoints}
    for v1_server_name in SERVER[version]:
        df_v1_server = df_version.loc[df_version["server"] == v1_server_name]
        df_endpoint_grouped = (
            df_v1_server.groupby(["endpoint"], dropna=False)
            .mean(numeric_only=True)
            .sort_values(by=["endpoint"])
        )
        label = LABEL[version][v1_server_name]
        datas[label] = df_endpoint_grouped[column_to_compare].tolist()

    new_df = pd.DataFrame(datas)
    title = f"Komparasi Semua Endpoint"
    y_label = [l for l in LABEL[version].values()]
    ax = new_df.plot(
        kind="bar",
        x="endpoint",
        y=y_label,
        ylabel="Transaksi per detik",
        xlabel="Endpoint",
        rot=0,
        width=0.85,
        figsize=(10, 5),
        color=COLOR,
        # fill=False,
    )
    bars = ax.patches
    hatches = [h for h in HATCH for j in range(len(new_df))]

    excel_filename = slugify(f"{version}-{title}") + ".xlsx"
    new_df.to_excel(os.path.join(PLOT_FOLDER, excel_filename))

    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    modify_ax(ax, title)

    logging.info(f"{version} Saving {title}")
    filename = slugify(f"{version}-{title}") + ".png"
    plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def create_chart_combine_all_endpoint(
    df_version: pd.DataFrame, column_to_compare: str, version: str
):
    title = f"Kombinasi semua endpoint"
    df_server_grouped = df_version.groupby(["server"], dropna=False).mean(
        numeric_only=True
    )
    ax = df_server_grouped.plot(
        kind="bar",
        y="transaction_rate",
        ylabel="Transaksi per detik",
        xlabel="Endpoint",
        rot=0,
        width=0.85,
        figsize=(10, 5),
        color=COLOR,
    )
    bars = ax.patches
    hatches = [h for h in HATCH for j in range(len(df_server_grouped))]

    excel_filename = slugify(f"{version}-{title}") + ".xlsx"
    df_server_grouped.to_excel(os.path.join(PLOT_FOLDER, excel_filename))

    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    modify_ax(ax, title)

    logging.info(f"{version} Saving {title}")
    filename = slugify(f"{version}-{title}") + ".png"
    plt.savefig(os.path.join(PLOT_FOLDER, filename), bbox_inches="tight")


def create_chart_siege_result(input_file):
    logging.info(f"Creating chart from {input_file}")
    df = pd.read_excel(input_file, sheet_name="All")
    # df = df.loc[~df["endpoint"].isin(EXCLUDE_ENDPOINT_ALL)]

    data_frames = split_dataframe_per_version(df)
    column_to_compare = "transaction_rate"

    for version in data_frames:
        df_version = data_frames[version]
        excluded_endpoint = ENDPOINT_EXCLUDE_VERSION[version]
        df_version = df_version.loc[~df_version["endpoint"].isin(excluded_endpoint)]
        endpoints = df_version["endpoint"].unique()
        for endpoint in endpoints:
            create_chart_per_endpoint(endpoint, df_version, version, column_to_compare)
        create_chart_all_endpoint(df_version, column_to_compare, version)
        create_chart_combine_all_endpoint(df_version, column_to_compare, version)


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
