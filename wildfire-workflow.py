import os
import time
import subprocess
import logging
import json

import numpy as np
from sage_data_client import query
import pandas as pd
from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S')


def sesctl_call(command):
    # we put 1 second sleep to push each command slowly
    # the scheduler may become inconsistent on jobs when issuing
    # multiple job changes at a high rate
    time.sleep(1)
    my_env = os.environ.copy()
    my_env.update({
        "SES_HOST": os.getenv("SES_HOST"),
        "SES_USER_TOKEN": os.getenv("SES_USER_TOKEN", ""),
    })
    sesctl_stat = subprocess.Popen(
        [command],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=my_env,
    )
    stat, err = sesctl_stat.communicate()
    if sesctl_stat.returncode != 0:
        raise Exception(f'{command} failed: {stat}')
    if err != None:
        raise Exception(f'failed to get job list from the scheduler: {err}')
    return stat


# fill_job_id_if_exists fills job ID of the nodes if the job exists
# in the scheudler. Note that this uses bash commands.
def fill_job_id_if_exists(df: pd.DataFrame) -> pd.DataFrame:
    command = "sesctl stat | tail -n +3 | awk '{print $1, $2}'"
    stat = sesctl_call(command)
    for l in stat.decode().split("\n"):
        if l == "":
            continue
        sp = l.split(" ")
        if len(sp) != 2:
            raise Exception(f'failed to split the line: {l}')
        job_id, job_name = sp
        df.loc[df["job_name"] == job_name, "job_id"] = job_id
    return df


def submit_job(file_path):
    command = f'sesctl submit --file-path {file_path}'
    result = sesctl_call(command)
    logging.info(result.decode())


def resubmit_job(job_id, file_path):
    command = f'sesctl rm --suspend {job_id}'
    result = sesctl_call(command)
    logging.info(result.decode())
    command = f'sesctl edit {job_id} --file-path {file_path}'
    result = sesctl_call(command)
    logging.info(result.decode())
    command = f'sesctl submit --job-id {job_id}'
    result = sesctl_call(command)
    logging.info(result.decode())


def get_smoke_data_from_sage(df, prob_threshold=0.5) -> bool:
    time_window = "-1h"
    vsns = '|'.join(df["vsn"].to_list())
    df = query(start=time_window, filter=
        {
            "name": "env.smoke.tile_probs",
            "vsn": vsns,
        },
    )
    ret = False
    for vsn, _df in df.groupby("meta.vsn"):
        detected = False
        for _, r in _df.iterrows():
            v = np.array(json.loads(r.value))
            smoke = np.argwhere(v.squeeze() > prob_threshold)
            if len(smoke) >= 1:
                logging.info(f'{vsn} detected smoke. timestamp {r["timestamp"]} at {smoke}th tiles')
                detected = True
                ret = True
        if not detected:
            logging.info(f'no smoke detected on {vsn} within {time_window} ')
    return ret


def set_wildfire_active():
    wildfire_file = "wildfire"
    with open(wildfire_file, "w") as file:
        file.write(time.time())


# is_wildfire_active returns whethere reported wildfire is active
# or not, in a given time window
def is_wildfire_active(since_second=3600) -> bool:
    wildfire_file = "wildfire"
    if os.path.exists(wildfire_file):
        with open(wildfire_file, "r") as file:
            t = float(file.read().strip())
            if time.time() - t < since_second:
                return True
            else:
                return False
    else:
        return False


def update_job(df):
    for _, r in df.iterrows():
        env = Environment(loader=FileSystemLoader(searchpath="./"))
        template = env.get_template("smoke-detection-job-template.yaml")
        job_file_path = f'{r.job_name}.yaml'
        with open(job_file_path, "w") as file:
            file.write(template.render(json.loads(r.to_json())))
        if r["job_id"] == -1:
            submit_job(job_file_path)
        else:
            resubmit_job(r["job_id"], job_file_path)


logging.info(f'reading nodes.csv...')
df = pd.read_csv("nodes.csv")
df["job_id"] = -1
df["job_name"] = "wildfire-" + df["vsn"]
is_smoke_detected = get_smoke_data_from_sage(df, prob_threshold=0.7)
if is_smoke_detected:
    logging.info('smoke detected. setting wildfire timestamp to now')
    set_wildfire_active()

df = fill_job_id_if_exists(df)

for _, r in df.iterrows():
    logging.info(f'registered {json.loads(r.to_json())}')

if is_wildfire_active():
    logging.info("wildfire detected. Adjusting smoke detection execution interval to every 5 minutes")
    df["interval"] = '"5/* * * * *\"'
else:
    logging.info("no wildfire detected. Adjusting smoke detection execution interval to every 30 minutes")
    df["interval"] = '"30/* * * * *"'

logging.info("updating jobs...")
update_job(df)
logging.info("done")