#!/usr/bin/env python3
"""Fake worker process that exercises the real subprocess contract.

Reads JACKY_KANBAN_TASK from env, heartbeats periodically, does short
work, completes via the CLI. Designed to be spawned by the dispatcher
exactly the way `jacky chat -q` would be, minus the LLM cost.
"""

import json
import os
import subprocess
import time


def main():
    tid = os.environ["JACKY_KANBAN_TASK"]
    workspace = os.environ.get("JACKY_KANBAN_WORKSPACE", "")

    # Announce via CLI (goes through real argparse + init_db + etc)
    subprocess.run(
        ["jacky", "kanban", "heartbeat", tid, "--note", "started"],
        check=True, capture_output=True,
    )

    # Simulate work with periodic heartbeats
    for i in range(3):
        time.sleep(0.3)
        subprocess.run(
            ["jacky", "kanban", "heartbeat", tid, "--note", f"progress {i+1}/3"],
            check=True, capture_output=True,
        )

    # Complete with structured handoff
    subprocess.run(
        [
            "jacky", "kanban", "complete", tid,
            "--summary", f"real-subprocess worker finished {tid}",
            "--metadata", json.dumps({
                "workspace": workspace,
                "worker_pid": os.getpid(),
                "iterations": 3,
            }),
        ],
        check=True, capture_output=True,
    )


if __name__ == "__main__":
    main()
