"""Run bounded CTSI comparisons on the Pi using fresh local archives."""

import argparse
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path



CONTROL = bytes.fromhex("0043545349ff0a8000")


def sample(pid, device):
    status = Path(f"/proc/{pid}/status")
    stat = Path(f"/proc/{pid}/stat")
    try:
        rss = next(int(line.split()[1]) for line in status.read_text().splitlines()
                   if line.startswith("VmRSS:"))
        fields = stat.read_text().rsplit(")", 1)[1].split()
        cpu_ticks = int(fields[11]) + int(fields[12])
    except (FileNotFoundError, StopIteration):
        rss = cpu_ticks = None
    throttle = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
    return dict(monotonic_ns=time.monotonic_ns(), process_rss_kib=rss,
                process_cpu_ticks=cpu_ticks, load=os.getloadavg(),
                temperature_millic=int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()),
                throttled=throttle.stdout.strip() if throttle.returncode == 0 else None,
                disk_stats=list(map(int, (device / "stat").read_text().split())))


def percentiles(values):
    values = sorted(values)
    if not values:
        return {}
    return {name: values[math.ceil(q * len(values)) - 1] / 1e6
            for name, q in (("p50", .50), ("p95", .95), ("p99", .99), ("max", 1))}


def run(directory, options, polls, device):
    directory.mkdir(mode=0o700)
    archive = directory / "observations.sqlite3"
    signal = directory / "control.bin"
    signal.write_bytes(CONTROL)
    events_file = directory / "events.jsonl"
    samples = []
    with events_file.open("w") as output:
        command = [sys.executable, "-m", "software.ctsi.receiver", "--archive", str(archive),
                   "--polls", str(polls), "--signal-file", str(signal),
                   "--control-id", "storage-control", "--diagnostics", *options]
        with subprocess.Popen(command, stderr=output) as child:
            try:
                while child.poll() is None:
                    samples.append(sample(child.pid, device))
                    try:
                        child.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                if child.poll() is None:
                    child.kill()
            if child.returncode:
                raise RuntimeError(f"receiver exited {child.returncode}; see {events_file}")
    (directory / "system.json").write_text(json.dumps(samples, indent=2))
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    commits = [event for event in events if event["status"] == "committed"]
    drops = [event for event in events if event["status"] == "dropped"]
    acquisitions = [event for event in events if event["status"] in
                    (("queued", "dropped") if "--buffered" in options else ("committed",))]
    with closing(sqlite3.connect(archive)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        rows = connection.execute("SELECT id, payload, sha256 FROM raw_observations ORDER BY id").fetchall()
    digest = hashlib.sha256(CONTROL).hexdigest()
    if (integrity != "ok" or len(acquisitions) != polls or len(rows) != len(commits)
            or len(rows) + len(drops) != polls
            or rows != [(event["observation_id"], CONTROL, digest) for event in commits]
            or ("--buffered" in options and [event["sequence"] for event in commits]
                != [event["sequence"] for event in acquisitions if event["status"] == "queued"])):
        raise RuntimeError(f"archive verification failed for {archive}")
    disk = [last - first for first, last in zip(samples[0]["disk_stats"], samples[-1]["disk_stats"])]
    ticks = [s["process_cpu_ticks"] for s in samples if s["process_cpu_ticks"] is not None]
    return dict(acquired=polls, queued=sum(e["status"] == "queued" for e in events),
                committed=len(commits), dropped=len(drops), integrity=integrity,
                skipped_ticks=sum(event["missed_ticks"] for event in acquisitions),
                transaction_ms=percentiles([event["transaction_ns"] for event in commits]),
                acquisition_to_transaction_ms=percentiles([event["queue_delay_ns"] for event in commits]),
                start_lateness_ms=percentiles([event["lateness_ns"] for event in acquisitions]),
                start_interval_ms=percentiles([b["started_ns"] - a["started_ns"]
                                               for a, b in zip(acquisitions, acquisitions[1:])]),
                sampled_cpu_seconds=(max(ticks) - min(ticks)) / os.sysconf("SC_CLK_TCK") if ticks else None,
                peak_sampled_rss_kib=max((s["process_rss_kib"] for s in samples
                                          if s["process_rss_kib"] is not None), default=None),
                max_temperature_c=max(s["temperature_millic"] for s in samples) / 1000,
                throttled=sorted({s["throttled"] for s in samples if s["throttled"] is not None}),
                disk_writes=disk[4], disk_write_ms=disk[7], disk_busy_ms=disk[9])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New output directory on the tested filesystem")
    parser.add_argument("--device", default="mmcblk0", help="Linux block device to sample")
    parser.add_argument("--polls", type=int, default=60, choices=range(2, 301), metavar="2..300")
    parser.add_argument("--rounds", type=int, default=2, choices=range(1, 4), metavar="1..3")
    args = parser.parse_args()
    args.directory.mkdir(mode=0o700)
    device = Path("/sys/class/block") / args.device
    modes = [("direct-full", ["--synchronous", "FULL"]),
             ("direct-normal", ["--synchronous", "NORMAL"]),
             ("buffered-full", ["--synchronous", "FULL", "--buffered", "16"])]
    results = {}
    for round_index in range(args.rounds):
        for index in range(len(modes)):
            name, options = modes[(index + round_index) % len(modes)]
            label = f"{round_index + 1}-{name}"
            results[label] = run(args.directory / label, options, args.polls, device)
            (args.directory / "summary.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
