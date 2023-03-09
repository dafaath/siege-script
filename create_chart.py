import pandas as pd
import sys
from slugify import slugify

import matplotlib.pyplot as plt
import os
import logging

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PLOT_FOLDER = os.path.join(THIS_FOLDER, "plot")

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)

V1_SERVER = ["alvinv1", "dafav1", "hanin"]
V2_SERVER = ["alvinv2", "dafav2"]
SERVER = {
    "v1": V1_SERVER,
    "v2": V2_SERVER,
}


def create_chart(input_file):
    logging.info(f"Creating chart from {input_file}")
    df = pd.read_excel(input_file, sheet_name="All")
    df_v1 = df[df["server"].isin(V1_SERVER)]
    df_v2 = df[df["server"].isin(V2_SERVER)]
    data_frames = {
        "v1": df_v1,
        "v2": df_v2,
    }
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

            title = f"{endpoint} Response Per Second"
            ax = new_df.plot(
                kind="bar",
                x="concurrent",
                y=SERVER[version],
                title=title,
            )

            for container in ax.containers:
                ax.bar_label(container)

            logging.info(f"{version} Saving {title}")
            filename = slugify(f"{version}-{title}") + ".png"
            plt.savefig(os.path.join(PLOT_FOLDER, filename))


def main():
    args = sys.argv
    if len(args) < 2:
        print(
            """Usage: python create_chart.py filename
filname is an xlsx file generated from get_summary.py script
example: create_chart.py summary/all.xlsx"""
        )
        sys.exit(1)

    create_chart(args[1])


if __name__ == "__main__":
    main()
