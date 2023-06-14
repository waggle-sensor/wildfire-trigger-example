## Wildfire Detection Workflow Example

```
[ start ]
    |
 submit jobs
    |
[ smoke not detected ] <-----
    |                       |
 plugin reported a smoke    | no more smoke detected
    |                       | 
[ smoke detected ] ----------
```

This example demonstrates a scientific scenario on detecting wildfires using Waggle nodes. The program in this example submits a job to target nodes for running [the smoke detector plugin](https://portal.sagecontinuum.org/apps/app/iperezx/wildfire-smoke-detection) using the camera view showing the area where wildfire can be spotted when occurs. The plugin in the job is set to be scheduled with a longer interval for the first time. Then, the program periodically reads detection results of the plugin via the Waggle data service in the cloud. When smoke is detected from the results, it shortens the scheduling interval of the plugin and resubmit the jobs, to make the plugin scheduled more frequently in the nodes. This will allow us to get more data to determine and track potential wildfire. After no more smoke is detected, the program returns the interval back.

## How To Run

This example needs a valid token to submit jobs to the Waggle edge scheduler. To obtain a token, go to [contact-us](https://sagecontinuum.org/docs/contact-us).

```bash
# in bash
export SES_HOST=https://es.sagecontinuum.org
export SES_USER_TOKEN=<<VALID TOKEN>>
```

This also needs the Waggle scheduler command-line-interface (CLI), `sesctl`, to manage jobs. To download the tool,

```bash
# the CLI tool depends on the computer's operating system and architecture
# in this example we download 0.22.6 version tool for Linux amd64 system
wget -O sesctl https://github.com/waggle-sensor/edge-scheduler/releases/download/0.22.6/sesctl-linux-amd64
chmod +x sesctl
```

### Populate nodes.csv

nodes.csv consists of nodes that the plugin will be run on,

```bash
vsn,stream
V002,bottom_camera
V003,left_camera
V004,left_camera
V005,top_camera
```

[Sage nodes portal](https://portal.sagecontinuum.org/nodes) lists Sage/Waggle nodes to monitor wildfire. You will add a row in the file with node's VSN and its camera stream that sees the targer area.

### Run The Workflow

The program needs to run in the cloud (or on your laptop). Runtime system can be linux crontab or a function-as-a-service (e.g., funcX).

```bash
python3 wildfire-workflow.py
```

### Output

When the program runs, it outputs status of the jobs on each node. If a smoke (possibly a wildfire) is detected, it will adjust the scheduling interval to every 5 minutes. Otherwise, it will set the interval to every 30 minutes.

```bash
2023/06/14 09:47:30 registered {'vsn': 'V002', 'stream': 'bottom_camera', 'job_id': '38', 'job_name': 'wildfire-V002'}
2023/06/14 09:47:30 registered {'vsn': 'V003', 'stream': 'left_camera', 'job_id': '39', 'job_name': 'wildfire-V003'}
2023/06/14 09:47:30 registered {'vsn': 'V004', 'stream': 'left_camera', 'job_id': '40', 'job_name': 'wildfire-V004'}
2023/06/14 09:47:30 registered {'vsn': 'V005', 'stream': 'top_camera', 'job_id': '41', 'job_name': 'wildfire-V005'}
2023/06/14 09:47:30 no wildfire detected. Adjusting smoke detection execution interval to every 30 minutes
2023/06/14 09:47:31 {
 "job_id": "38",
 "state": "Suspended"
}
2023/06/14 09:47:32 {
 "job_id": "38",
 "state": "Drafted"
}
2023/06/14 09:47:33 {
 "job_id": "38",
 "state": "Submitted"
}
...
```