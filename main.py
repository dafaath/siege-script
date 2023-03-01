import datetime
import json
import logging
import os
import subprocess
import sys
import time
import typing
import requests
import pandas as pd

CONFIGS = {}
with open("config.json", "r") as f:
    CONFIGS = json.load(f)

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIRECTORY = os.path.join(ROOT_DIRECTORY, "output")
LOG_DIRECTORY = os.path.join(ROOT_DIRECTORY, "log")

session_start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
log_filename = os.path.join(
    LOG_DIRECTORY,
    session_start_time + ".log",
)
logging.basicConfig(
    filename=log_filename,
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)

logger = logging.getLogger("server IoT Logger Session " + session_start_time)
logger.addHandler(logging.StreamHandler(sys.stdout))

# !Todo tambahkan komen
logger.info("🎬 Starting Session")
logger.info(f"Sleep time: {CONFIGS['sleep_time']}")
logger.info(f"Test time: {CONFIGS['test_time']}")
logger.info(f"Iteration: {CONFIGS['iteration']}")
logger.info(f"Concurrence: {CONFIGS['concurrence']}")


session_data = {}
for server in CONFIGS["server_to_test"]:
    server_name = server["name"]
    session_data[server_name] = {}

    credential: typing.Dict[str, str] = CONFIGS["credential"]
    logger.info(
        f"🔑 Logging in to {server_name} with {credential['username']} and {credential['password']}"
    )
    response = requests.post(
        server["url"] + "/user/login",
        {
            "username": credential["username"],
            "password": credential["password"],
        },
    )
    token = response.text
    header = f"Authorization: Bearer {token}"
    for endpoint in CONFIGS["endpoint_to_compare"]:
        run_identifier = f"{endpoint['method']} {endpoint['path']}"
        session_data[server_name][run_identifier] = {}
        for concurrent in CONFIGS["concurrence"]:
            session_data[server_name][run_identifier][concurrent] = []
            for i in range(1, CONFIGS["iteration"] + 1):
                commands = [
                    "siege",
                    f"-t{CONFIGS['test_time']}",
                    "-c",
                    f'"{str(concurrent)}"',
                ]
                if endpoint["method"].lower() in ["post", "put"]:
                    data_string = json.dumps(endpoint["data"]).replace('"', '\\"')
                    commands.append(
                        f'"{server["url"] + endpoint["path"]} {endpoint["method"]} {data_string}"'
                    )
                    commands.append("--content-type")
                    commands.append('"application/json"')
                else:
                    commands.append(f'"{server["url"] + endpoint["path"]}"')

                commands.append("--header")
                commands.append(f'"{header}"')

                if "verbose" in CONFIGS and CONFIGS["verbose"]:
                    commands.append("--verbose")

                logger.info("🦾 Running commands " + " ".join(commands))
                output = subprocess.run(
                    " ".join(commands), stdout=subprocess.PIPE, shell=True
                )
                if output.returncode != 0:
                    raise SystemError(output.stderr)

                json_output: dict = json.loads(output.stdout)

                session_data[server_name][run_identifier][concurrent].append(
                    json_output
                )

                logger.info(
                    f"🏁 Finished running commands for {server_name} {endpoint['path']} {endpoint['method']} {concurrent} {i}",
                )
                logger.info(f"📊 Output: {json_output}")

                output = {
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "server": server_name,
                    "endpoint": f"{endpoint['method']} {endpoint['path']}",
                    "concurrent": concurrent,
                    "iteration": i,
                    **json_output,
                }
                output_filename = os.path.join(
                    OUTPUT_DIRECTORY, f"{session_start_time}.xlsx"
                )
                logger.info(f"💾 Saving output to file {output_filename}")

                try:
                    df_dictionary = pd.DataFrame([output])
                    df = pd.concat([df, df_dictionary], ignore_index=True)  # type: ignore
                except NameError:
                    df = pd.DataFrame(output, index=[0])

                df.style.set_caption(
                    f"""Server IoT Test Session {session_start_time} 
                Sleep time: {CONFIGS['sleep_time']} 
                Test time: {CONFIGS['test_time']} 
                Iteration: {CONFIGS['iteration']} 
                Concurrence: {CONFIGS['concurrence']}"""
                )

                df_group_by_concurrent = df.groupby(
                    ["endpoint", "concurrent"], dropna=False
                ).mean()
                df_group_by_endpoint = df.groupby(["endpoint"], dropna=False).mean()

                writer = pd.ExcelWriter(output_filename, engine="xlsxwriter")

                # Write each dataframe to a different worksheet.
                df.to_excel(writer, sheet_name="All", index=False)
                df_group_by_concurrent.to_excel(
                    writer, sheet_name="Group By Concurrent", index=True
                )
                df_group_by_endpoint.to_excel(
                    writer, sheet_name="Group By Endpoint", index=True
                )

                # Close the Pandas Excel writer and output the Excel file.
                writer.close()

                logger.info(f"💾 Finish Saving output")

                logger.info(f"💤 Sleeping for {CONFIGS['sleep_time']} seconds")
                time.sleep(CONFIGS["sleep_time"])

logger.info("🎬 Finish Session")
