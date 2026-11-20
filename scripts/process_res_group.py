#!/usr/bin/env python3
"""Collect raw benchmark logs and produce a run-level group analysis."""

import argparse
import glob
import os
from pathlib import Path

from process_res import process_logs


LOG_PATTERN = "logs_docker-compose-*.yaml.log"


def collect_logs(inputs):
    log_paths = set()
    for item in inputs:
        matches = glob.glob(item, recursive=True)
        candidates = [Path(match) for match in matches] if matches else [Path(item)]

        for candidate in candidates:
            if candidate.is_file():
                log_paths.add(candidate.resolve())
            elif candidate.is_dir():
                log_paths.update(
                    path.resolve() for path in candidate.rglob(LOG_PATTERN) if path.is_file()
                )
            else:
                raise FileNotFoundError("Input path does not exist: {}".format(candidate))

    return sorted(log_paths)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Analyze every standard benchmark log found in the supplied directories. "
            "Runs with different seeds are aggregated as independent replicates."
        )
    )
    parser.add_argument(
        "directories",
        nargs="+",
        help="experiment directories, wildcard directory patterns, or explicit log files",
    )
    args = parser.parse_args(argv)
    log_paths = collect_logs(args.directories)
    if not log_paths:
        parser.error(
            "no {} files found in the supplied directories".format(LOG_PATTERN)
        )

    print(
        "Discovered {} benchmark log(s); aggregating metrics across runs.".format(
            len(log_paths)
        )
    )
    try:
        output_directory = Path(
            os.path.commonpath([str(path.parent) for path in log_paths])
        )
    except ValueError:
        output_directory = Path.cwd()
    process_logs(log_paths, output_directory / "comparison_stats.txt")


if __name__ == "__main__":
    main()
