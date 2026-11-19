# -*- coding: utf-8 -*-
"""Parse benchmark logs and report per-run and replicated-run statistics."""

import argparse
from collections import defaultdict
import csv
from itertools import combinations
import math
from pathlib import Path
import re
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats


AGENT_RE = re.compile(r"agent\d+")
CONFIG_RE = re.compile(
    r"(?P<platform>[A-Za-z0-9_-]+)-c(?P<containers>\d+)"
    r"-n(?P<agents>\d+)-r(?P<repeats>\d+)-ms(?P<message_size>\d+)"
    r"-(?P<workload>inform|query|cfp)-g(?P<group_size>\d+)"
    r"-m(?P<memory>[^-]+)-cpu(?P<cpus>[0-9.]+)"
    r"(?:-p(?P<period>\d+))?(?:-seed(?P<seed>-?\d+))?",
    re.IGNORECASE,
)

CONFIG_FIELDS = (
    "platform",
    "containers",
    "agents",
    "repeats",
    "message_size",
    "workload",
    "group_size",
    "memory",
    "cpus",
    "period",
    "seed",
)
MATCH_FIELDS = tuple(field for field in CONFIG_FIELDS if field != "platform")
SCALABILITY_FIELDS = tuple(
    field for field in CONFIG_FIELDS if field not in ("platform", "containers")
)

RUN_METRICS = (
    "mean_latency",
    "p95_latency",
    "init_duration",
    "throughput",
    "message_loss_rate",
)
RUN_METRIC_LABELS = {
    "mean_latency": "mean_latency [µs]",
    "p95_latency": "p95_latency [µs]",
    "init_duration": "init_duration [s]",
    "throughput": "throughput [messages/s]",
    "message_loss_rate": "message_loss_rate",
}

CSV_FIELDS = (
    "agents",
    "repetitions",
    "containers",
    "int protocol",
    "message size",
    "platform",
    "where",
    "seed",
    "Initialization time [s]",
    "Simulation time [s]",
    "latency [µs]",
    "Median latency [µs]",
    "Stddev [µs]",
    "Shapiro-Wilk",
    "Max memory [MiB]",
    "Avg memory [MiB]",
    "CPU in top 5% [threshold %]",
    "Messages lost",
    "Messages successful",
    "Messages lost %",
)


def parse_config(path):
    """Extract workload dimensions from a standard benchmark log or folder name."""
    for candidate in (path.name, path.parent.name):
        name = candidate
        for prefix in ("logs_docker-compose-", "docker-compose-", "logs_"):
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        match = CONFIG_RE.search(name)
        if match:
            values = match.groupdict()
            return {
                "platform": values["platform"].lower(),
                "containers": int(values["containers"]),
                "agents": int(values["agents"]),
                "repeats": int(values["repeats"]),
                "message_size": int(values["message_size"]),
                "workload": values["workload"].lower(),
                "group_size": int(values["group_size"]),
                "memory": values["memory"],
                "cpus": float(values["cpus"]),
                "period": int(values["period"]) if values["period"] else None,
                "seed": int(values["seed"]) if values["seed"] else None,
            }
    return None


def parse_timestamp(value):
    value = str(value).strip().strip("\"'")
    if re.fullmatch(r"-?\d+", value):
        return pd.Timestamp(int(value), unit="us")
    return pd.Timestamp(value)


def git_metadata():
    repo_root = Path(__file__).resolve().parents[1]
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    ).stdout
    return commit, bool(status.strip())


def distribution(values):
    if not values:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "median": None,
            "p50": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "min": None,
            "max": None,
            "skewness": None,
            "kurtosis": None,
            "shapiro_stat": None,
            "shapiro_p": None,
        }

    data = np.asarray(values, dtype=float)
    is_constant = bool(np.all(data == data[0]))
    shapiro_stat = None
    shapiro_p = None
    if 3 <= len(data) <= 5000 and not is_constant:
        shapiro_stat, shapiro_p = stats.shapiro(data)

    return {
        "count": int(len(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "median": float(np.median(data)),
        "p50": float(np.percentile(data, 50)),
        "p90": float(np.percentile(data, 90)),
        "p95": float(np.percentile(data, 95)),
        "p99": float(np.percentile(data, 99)),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "skewness": float(stats.skew(data)) if len(data) >= 3 and not is_constant else None,
        "kurtosis": float(stats.kurtosis(data)) if len(data) >= 4 and not is_constant else None,
        "shapiro_stat": float(shapiro_stat) if shapiro_stat is not None else None,
        "shapiro_p": float(shapiro_p) if shapiro_p is not None else None,
    }


def analyze_log(path, commit, worktree_dirty):
    messages = {}
    conversations = {}
    inits = []
    malformed_records = 0

    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            init_match = re.search(r"\| (init;.*)", line)
            if init_match:
                record = init_match.group(1).split(";")
                if len(record) == 4 and record[1] in ("initializing", "running"):
                    inits.append(parse_timestamp(record[3]))

            agent_match = re.search(r"\| (agent.*)", line)
            if not agent_match:
                continue
            record = agent_match.group(1).split(";")
            if len(record) < 7 or not (
                AGENT_RE.fullmatch(record[0]) and AGENT_RE.fullmatch(record[1])
            ):
                malformed_records += 1
                continue

            message = messages.setdefault(record[3], {})
            conversation = conversations.setdefault(record[4], {})
            if record[5] == "S":
                message.update(
                    {"sender": record[0], "receiver": record[1], "sendtime": record[6]}
                )
                conversation.update(
                    {"sender": record[0], "receiver": record[1], "sendtime": record[6]}
                )
            elif record[5] == "R":
                message.update({"receivetime": record[6]})
                conversation.update({"receivetime": record[6]})

    if not inits:
        raise ValueError("No initialization timestamps found in {}".format(path))

    init_start = min(inits)
    init_end = max(inits)
    init_duration = (init_end - init_start).total_seconds()

    def latencies(records):
        values = []
        sent = 0
        received_without_send = 0
        for details in records.values():
            has_send = "sendtime" in details
            has_receive = "receivetime" in details
            sent += int(has_send)
            received_without_send += int(has_receive and not has_send)
            if has_send and has_receive:
                start = parse_timestamp(details["sendtime"])
                end = parse_timestamp(details["receivetime"])
                values.append((end - start).total_seconds() * 1_000_000)
        lost = sent - len(values)
        loss_rate = float(lost) / sent if sent else None
        return values, sent, lost, received_without_send, loss_rate

    message_latencies, messages_sent, messages_lost, orphan_messages, message_loss_rate = (
        latencies(messages)
    )
    (
        conversation_latencies,
        conversations_sent,
        conversations_lost,
        orphan_conversations,
        conversation_loss_rate,
    ) = latencies(conversations)
    message_stats = distribution(message_latencies)
    conversation_stats = distribution(conversation_latencies)

    all_times = [
        parse_timestamp(details["receivetime"])
        for records in (messages, conversations)
        for details in records.values()
        if "receivetime" in details
    ]
    if all_times:
        simulation_start = min(all_times)
        simulation_end = max(all_times)
        simulation_duration = (simulation_end - simulation_start).total_seconds()
    else:
        simulation_start = None
        simulation_end = None
        simulation_duration = None

    throughput = None
    if simulation_duration is not None and simulation_duration > 0:
        throughput = len(message_latencies) / simulation_duration

    run_metrics = {
        "mean_latency": message_stats["mean"],
        "p95_latency": message_stats["p95"],
        "init_duration": init_duration,
        "throughput": throughput,
        "message_loss_rate": message_loss_rate,
    }
    return {
        "path": path,
        "commit": commit,
        "worktree_dirty": worktree_dirty,
        "config": parse_config(path),
        "init_start": init_start,
        "init_end": init_end,
        "init_duration": init_duration,
        "simulation_start": simulation_start,
        "simulation_end": simulation_end,
        "simulation_duration": simulation_duration,
        "messages_sent": messages_sent,
        "messages_lost": messages_lost,
        "orphan_messages": orphan_messages,
        "conversations_sent": conversations_sent,
        "conversations_lost": conversations_lost,
        "orphan_conversations": orphan_conversations,
        "message_loss_rate": message_loss_rate,
        "conversation_loss_rate": conversation_loss_rate,
        "message_stats": message_stats,
        "conversation_stats": conversation_stats,
        "message_latencies": message_latencies,
        "conversation_latencies": conversation_latencies,
        "malformed_records": malformed_records,
        "run_metrics": run_metrics,
    }


def format_value(value):
    if value is None:
        return "n/a"
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return "n/a"
    if isinstance(value, (float, np.floating)):
        return "{:.6g}".format(float(value))
    return str(value)


def format_config(config):
    if config is None:
        return "not recognized from filename or directory"
    return ", ".join(
        "{}={}".format(name, format_value(config[name])) for name in CONFIG_FIELDS
    )


def save_histogram(values, output_path, title, xlabel, color):
    data = np.asarray(values, dtype=float)
    if data.ndim != 1 or not np.all(np.isfinite(data)):
        raise ValueError("Histogram values must be a one-dimensional finite sequence.")

    figure, axis = plt.subplots()
    try:
        axis.set_title("{} (n={})".format(title, len(data)))
        axis.set_xlabel(xlabel)
        axis.set_ylabel("Messages")
        if data.size == 0:
            axis.text(
                0.5,
                0.5,
                "No successful latency observations",
                horizontalalignment="center",
                verticalalignment="center",
                transform=axis.transAxes,
            )
            axis.set_yticks([])
        else:
            axis.hist(
                data,
                bins="auto",
                color=color,
                edgecolor="black",
                alpha=0.75,
                label="Observed",
            )
            median = float(np.median(data))
            p95 = float(np.percentile(data, 95))
            if median == p95:
                axis.axvline(median, color="black", linestyle="--", label="Median / p95")
            else:
                axis.axvline(median, color="black", linestyle="--", label="Median")
                axis.axvline(p95, color="red", linestyle=":", label="p95")
            axis.legend()
        figure.tight_layout()
        figure.savefig(str(output_path))
    finally:
        plt.close(figure)


def independent_run_count(run, runs):
    config = run["config"]
    if config is None:
        return 1

    fields = tuple(field for field in CONFIG_FIELDS if field != "seed")
    return sum(
        1
        for candidate in runs
        if candidate["config"] is not None
        and all(candidate["config"][field] == config[field] for field in fields)
    )


def write_run_report(run, independent_runs_supplied):
    path = run["path"]
    output_path = path.with_name("stats_{}.txt".format(path.name))
    message = run["message_stats"]
    conversation = run["conversation_stats"]

    with output_path.open("w", encoding="utf-8") as outfile:
        outfile.write("Input log: {}\n".format(path))
        outfile.write("Git commit: {}\n".format(run["commit"]))
        outfile.write(
            "Git worktree dirty: {}\n".format("yes" if run["worktree_dirty"] else "no")
        )
        outfile.write("Configuration: {}\n\n".format(format_config(run["config"])))

        outfile.write("Initialization started at: {}\n".format(run["init_start"]))
        outfile.write("Initialization ended at: {}\n".format(run["init_end"]))
        outfile.write(
            "Initialization duration: {} seconds\n".format(run["init_duration"])
        )
        outfile.write("Simulation started: {}\n".format(run["simulation_start"] or "n/a"))
        outfile.write("Simulation ended: {}\n".format(run["simulation_end"] or "n/a"))
        outfile.write(
            "Simulation duration: {} seconds\n".format(
                format_value(run["simulation_duration"])
            )
        )

        outfile.write("\nMessages sent: {}\n".format(run["messages_sent"]))
        outfile.write("Messages successful: {}\n".format(message["count"]))
        outfile.write("Messages lost: {}\n".format(run["messages_lost"]))
        outfile.write("Message loss rate: {}\n".format(format_value(run["message_loss_rate"])))
        outfile.write("Message receives without a send record: {}\n".format(run["orphan_messages"]))
        outfile.write("Conversations sent: {}\n".format(run["conversations_sent"]))
        outfile.write("Conversations successful: {}\n".format(conversation["count"]))
        outfile.write("Conversations lost: {}\n".format(run["conversations_lost"]))
        outfile.write(
            "Conversation loss rate: {}\n".format(format_value(run["conversation_loss_rate"]))
        )
        outfile.write(
            "Conversation receives without a send record: {}\n".format(
                run["orphan_conversations"]
            )
        )
        outfile.write("Malformed agent records skipped: {}\n".format(run["malformed_records"]))

        for label, values in (
            ("Message latency", message),
            ("Conversation latency", conversation),
        ):
            outfile.write("\n{} (microseconds; within this run):\n".format(label))
            for name in ("count", "mean", "std", "median", "p50", "p90", "p95", "p99", "min", "max"):
                outfile.write("  {}: {}\n".format(name, format_value(values[name])))
            outfile.write("  skewness: {}\n".format(format_value(values["skewness"])))
            outfile.write("  kurtosis: {}\n".format(format_value(values["kurtosis"])))
            if values["shapiro_p"] is not None:
                outfile.write(
                    "  Shapiro-Wilk statistic: {}; p-value: {}\n".format(
                        format_value(values["shapiro_stat"]),
                        format_value(values["shapiro_p"]),
                    )
                )
            else:
                outfile.write("  Shapiro-Wilk: not computed (requires 3-5000 non-constant values)\n")

        outfile.write("\nRun-level metrics for cross-run analysis:\n")
        outfile.write("  Message latency metrics use microseconds.\n")
        outfile.write("  Successful-message throughput (messages/second): {}\n".format(
            format_value(run["run_metrics"]["throughput"])
        ))
        outfile.write(
            "  Independent log runs supplied: {}\n".format(independent_runs_supplied)
        )
        if independent_runs_supplied < 2:
            outfile.write(
                "  Run-level confidence intervals and significance tests: unavailable; "
                "supply independent log files for this workload.\n"
            )
        outfile.write(
            "\nLatency percentiles summarize messages within this run; they are not "
            "independent-run confidence intervals.\n"
        )

        mean_diff = message["mean"]
        median_diff = message["median"]
        std_dev_diff = (
            float(np.std(run["message_latencies"]))
            if run["message_latencies"]
            else None
        )
        outfile.write(
            "{};{};{};{};{};{};;;;{};{}\n".format(
                format_value(run["init_duration"]),
                format_value(run["simulation_duration"]),
                format_value(mean_diff),
                format_value(median_diff),
                format_value(std_dev_diff),
                format_value(message["shapiro_stat"]),
                run["messages_lost"],
                message["count"],
            )
        )
        outfile.write(
            "{};{}\n".format(
                format_value(conversation["mean"]),
                format_value(
                    float(np.std(run["conversation_latencies"]))
                    if run["conversation_latencies"]
                    else None
                ),
            )
        )

    save_histogram(
        run["message_latencies"],
        path.with_name("histogram{}.png".format(path.name)),
        "Histogram of Message Latency",
        "Latency [µs]",
        "blue",
    )
    save_histogram(
        run["conversation_latencies"],
        path.with_name("histogram_conversations{}.png".format(path.name)),
        "Histogram of Conversation Latency",
        "Latency [µs]",
        "orange",
    )
    return output_path


def memory_metrics(log_path):
    log_name = log_path.name
    if log_name.startswith("logs_"):
        log_name = log_name[len("logs_") :]
    if log_name.endswith(".log"):
        log_name = log_name[: -len(".log")]

    memory_files = sorted(log_path.parent.glob("mem_{}-mas*.log".format(log_name)))
    server_log = log_path.parent / "mem_{}-xmpp.log".format(log_name)
    if server_log.is_file():
        memory_files.append(server_log)

    memory_values = []
    cpu_values = []
    for memory_file in memory_files:
        if memory_file.stat().st_size == 0:
            continue
        frame = pd.read_csv(
            memory_file,
            sep=";",
            header=None,
            names=("timestamp", "container", "memory", "cpu"),
            dtype=str,
        )
        if frame.empty:
            continue
        used = pd.to_numeric(
            frame["memory"].str.extract(r"(\d+(?:\.\d+)?)", expand=False),
            errors="coerce",
        ).dropna()
        cpu = pd.to_numeric(
            frame["cpu"].str.rstrip("%"),
            errors="coerce",
        ).dropna()
        memory_values.extend(used.tolist())
        cpu_values.extend(cpu.tolist())

    return {
        "max_memory": float(np.max(memory_values)) if memory_values else None,
        "avg_memory": float(np.mean(memory_values)) if memory_values else None,
        "cpu_top5_threshold": float(np.percentile(cpu_values, 95)) if cpu_values else None,
    }


def write_results_csv(runs, output_path):
    with output_path.open("w", encoding="utf-8-sig", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for run in runs:
            config = run["config"] or {}
            memory = memory_metrics(run["path"])
            message = run["message_stats"]
            writer.writerow(
                {
                    "agents": config.get("agents"),
                    "repetitions": config.get("repeats"),
                    "containers": config.get("containers"),
                    "int protocol": config.get("workload"),
                    "message size": config.get("message_size"),
                    "platform": config.get("platform"),
                    "where": run["path"].parent.name,
                    "seed": config.get("seed"),
                    "Initialization time [s]": run["init_duration"],
                    "Simulation time [s]": run["simulation_duration"],
                    "latency [µs]": message["mean"],
                    "Median latency [µs]": message["median"],
                    "Stddev [µs]": message["std"],
                    "Shapiro-Wilk": message["shapiro_stat"],
                    "Max memory [MiB]": memory["max_memory"],
                    "Avg memory [MiB]": memory["avg_memory"],
                    "CPU in top 5% [threshold %]": memory["cpu_top5_threshold"],
                    "Messages lost": run["messages_lost"],
                    "Messages successful": message["count"],
                    "Messages lost %": (
                        run["message_loss_rate"] * 100
                        if run["message_loss_rate"] is not None
                        else None
                    ),
                }
            )
    return output_path


def mean_confidence_interval(values, confidence=0.95):
    data = np.asarray(values, dtype=float)
    if len(data) < 2:
        return None, None
    mean = float(np.mean(data))
    standard_error = float(np.std(data, ddof=1) / math.sqrt(len(data)))
    if standard_error == 0:
        return mean, mean
    critical = float(stats.t.ppf((1 + confidence) / 2.0, len(data) - 1))
    return mean - critical * standard_error, mean + critical * standard_error


def welch_comparison(first, second):
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if len(first) < 2 or len(second) < 2:
        return None

    first_mean = float(np.mean(first))
    second_mean = float(np.mean(second))
    difference = first_mean - second_mean
    first_component = float(np.var(first, ddof=1)) / len(first)
    second_component = float(np.var(second, ddof=1)) / len(second)
    standard_error = math.sqrt(first_component + second_component)
    if standard_error == 0:
        return {
            "difference": difference,
            "ci_low": difference,
            "ci_high": difference,
            "p_value": 1.0 if difference == 0 else 0.0,
            "df": None,
        }

    denominator = (
        first_component ** 2 / (len(first) - 1)
        + second_component ** 2 / (len(second) - 1)
    )
    degrees_freedom = (first_component + second_component) ** 2 / denominator
    statistic = difference / standard_error
    p_value = 2.0 * stats.t.sf(abs(statistic), degrees_freedom)
    critical = stats.t.ppf(0.975, degrees_freedom)
    return {
        "difference": difference,
        "ci_low": difference - critical * standard_error,
        "ci_high": difference + critical * standard_error,
        "p_value": float(p_value),
        "df": float(degrees_freedom),
    }


def holm_adjust(p_values):
    if not p_values:
        return []
    order = np.argsort(p_values)
    adjusted = [0.0] * len(p_values)
    running_max = 0.0
    count = len(p_values)
    for rank, original_index in enumerate(order):
        candidate = min(1.0, (count - rank) * float(p_values[original_index]))
        running_max = max(running_max, candidate)
        adjusted[int(original_index)] = running_max
    return adjusted


def _key(config, fields):
    return tuple(config[field] for field in fields)


def _key_label(config, fields):
    return ", ".join(
        "{}={}".format(field, format_value(config[field])) for field in fields
    )


def _run_summary_lines(runs):
    groups = defaultdict(list)
    for run in runs:
        config = run["config"]
        if config is not None:
            groups[_key(config, CONFIG_FIELDS)].append(run)

    lines = []
    lines.append("Run-level descriptive statistics (each input file is one independent run)")
    for group_key in sorted(groups, key=str):
        group_runs = groups[group_key]
        config = group_runs[0]["config"]
        lines.append("\nConfiguration: {}".format(_key_label(config, CONFIG_FIELDS)))
        for metric in RUN_METRICS:
            values = [
                run["run_metrics"][metric]
                for run in group_runs
                if run["run_metrics"][metric] is not None
            ]
            n = len(values)
            mean = float(np.mean(values)) if values else None
            standard_deviation = (
                float(np.std(values, ddof=1)) if n >= 2 else None
            )
            ci_low, ci_high = mean_confidence_interval(values)
            lines.append(
                "  {}: n_runs={}, mean={}, sample_sd={}, 95%_CI=[{}, {}]".format(
                    RUN_METRIC_LABELS[metric],
                    n,
                    format_value(mean),
                    format_value(standard_deviation),
                    format_value(ci_low),
                    format_value(ci_high),
                )
            )
            if n < 2:
                lines.append(
                    "    CI unavailable: at least two independent runs with this metric are required."
                )
    if not groups:
        lines.append("No input filenames contained recognizable workload configuration metadata.")
    return lines


def _comparison_lines(runs):
    groups = defaultdict(lambda: defaultdict(list))
    for run in runs:
        config = run["config"]
        if config is not None:
            groups[_key(config, MATCH_FIELDS)][config["platform"]].append(run)

    lines = [
        "",
        "Matched platform comparisons",
        "Method: two-sided Welch t-tests on independent per-log run metrics; "
        "95% Welch confidence intervals for mean differences; Holm adjustment "
        "within each matched configuration and metric. Tests are approximate; "
        "interpret results cautiously when replication is low.",
        "Latency metrics and differences are in microseconds; initialization time is in seconds.",
        "Difference direction is platform A minus platform B.",
    ]
    found_comparison = False
    for group_key in sorted(groups, key=str):
        platform_runs = groups[group_key]
        if len(platform_runs) < 2:
            continue
        found_comparison = True
        first_config = next(iter(next(iter(platform_runs.values()))))["config"]
        lines.append("\nMatched workload: {}".format(_key_label(first_config, MATCH_FIELDS)))
        for metric in RUN_METRICS:
            pair_results = []
            for platform_a, platform_b in combinations(sorted(platform_runs), 2):
                values_a = [
                    run["run_metrics"][metric]
                    for run in platform_runs[platform_a]
                    if run["run_metrics"][metric] is not None
                ]
                values_b = [
                    run["run_metrics"][metric]
                    for run in platform_runs[platform_b]
                    if run["run_metrics"][metric] is not None
                ]
                if len(values_a) < 2 or len(values_b) < 2:
                    pair_results.append(
                        (
                            platform_a,
                            platform_b,
                            len(values_a),
                            len(values_b),
                            None,
                        )
                    )
                else:
                    pair_results.append(
                        (
                            platform_a,
                            platform_b,
                            len(values_a),
                            len(values_b),
                            welch_comparison(values_a, values_b),
                        )
                    )
            tested = [entry for entry in pair_results if entry[4] is not None]
            adjusted = holm_adjust([entry[4]["p_value"] for entry in tested])
            adjusted_by_pair = {
                (entry[0], entry[1]): adjusted[index]
                for index, entry in enumerate(tested)
            }
            for platform_a, platform_b, count_a, count_b, result in pair_results:
                if result is None:
                    lines.append(
                        "  {} vs {} / {}: not tested (runs: {}, {}; need at least 2 per platform).".format(
                            platform_a, platform_b, metric, count_a, count_b
                        )
                    )
                    continue
                adjusted_p = adjusted_by_pair[(platform_a, platform_b)]
                lines.append(
                    "  {} vs {} / {}: n=({}, {}), mean_difference={}, "
                    "95%_CI=[{}, {}], Welch_df={}, p={}, Holm_p={}{}".format(
                        platform_a,
                        platform_b,
                        RUN_METRIC_LABELS[metric],
                        count_a,
                        count_b,
                        format_value(result["difference"]),
                        format_value(result["ci_low"]),
                        format_value(result["ci_high"]),
                        format_value(result["df"]),
                        format_value(result["p_value"]),
                        format_value(adjusted_p),
                        " (adjusted p < 0.05)" if adjusted_p < 0.05 else "",
                    )
                )
    if not found_comparison:
        lines.append(
            "No matched workload configurations with at least two platforms were supplied."
        )
    return lines


def _scalability_lines(runs):
    groups = defaultdict(lambda: defaultdict(list))
    for run in runs:
        config = run["config"]
        if config is not None:
            groups[_key(config, SCALABILITY_FIELDS)][config["containers"]].append(run)

    lines = [
        "",
        "Scalability efficiency",
        "For fixed workload dimensions, throughput speedup = mean throughput at C "
        "containers / mean throughput at 1 container; efficiency = speedup / C * 100%.",
    ]
    found = False
    for group_key in sorted(groups, key=str):
        container_runs = groups[group_key]
        if 1 not in container_runs or len(container_runs) < 2:
            continue
        baseline_values = [
            run["run_metrics"]["throughput"]
            for run in container_runs[1]
            if run["run_metrics"]["throughput"] is not None
        ]
        if not baseline_values:
            continue
        baseline = float(np.mean(baseline_values))
        if baseline <= 0:
            continue
        config = next(iter(next(iter(container_runs.values()))))["config"]
        lines.append("\nWorkload: {}".format(_key_label(config, SCALABILITY_FIELDS)))
        found = True
        for container_count in sorted(container_runs):
            if container_count == 1:
                continue
            values = [
                run["run_metrics"]["throughput"]
                for run in container_runs[container_count]
                if run["run_metrics"]["throughput"] is not None
            ]
            if not values:
                lines.append(
                    "  C={}: unavailable (no positive-duration throughput observations).".format(
                        container_count
                    )
                )
                continue
            throughput = float(np.mean(values))
            speedup = throughput / baseline
            efficiency = speedup / container_count * 100.0
            lines.append(
                "  C={}: n_runs={}, mean_throughput={}, speedup={}, efficiency={}%, "
                "baseline_n_runs={}".format(
                    container_count,
                    len(values),
                    format_value(throughput),
                    format_value(speedup),
                    format_value(efficiency),
                    len(baseline_values),
                )
            )
    if not found:
        lines.append("Unavailable: matching one-container baseline logs were not supplied.")
    return lines


def _regression_lines(runs):
    lines = [
        "",
        "Run-level OLS regression diagnostics",
        "Predictors: varying container count, agent count, message size and group size, "
        "plus platform/workload indicators when they vary. Each log contributes one row.",
    ]
    usable = [
        run
        for run in runs
        if run["config"] is not None
    ]
    if len(usable) < 3:
        lines.append("Regression unavailable: fewer than 3 configured independent runs.")
        return lines

    configs = [run["config"] for run in usable]
    feature_columns = []
    for field in ("containers", "agents", "message_size", "group_size"):
        values = np.asarray([config[field] for config in configs], dtype=float)
        if np.ptp(values) > 0:
            feature_columns.append((field, values))
    for field in ("platform", "workload"):
        categories = sorted(set(config[field] for config in configs))
        for category in categories[1:]:
            feature_columns.append(
                (
                    "{}={}".format(field, category),
                    np.asarray(
                        [1.0 if config[field] == category else 0.0 for config in configs]
                    ),
                )
            )

    predictors = [name for name, _ in feature_columns]
    if not predictors:
        lines.append(
            "Regression unavailable: no workload or platform predictors vary across runs."
        )
        return lines
    matrix = np.column_stack(
        [np.ones(len(usable))]
        + [values for _, values in feature_columns]
    )
    rank = int(np.linalg.matrix_rank(matrix))
    if rank < matrix.shape[1]:
        lines.append(
            "Regression unavailable: predictor matrix is rank-deficient "
            "({} columns, rank {}).".format(matrix.shape[1], rank)
        )
        return lines
    if len(usable) <= rank:
        lines.append(
            "Regression unavailable: {} independent runs do not exceed the {} fitted "
            "parameters.".format(len(usable), rank)
        )
        return lines

    lines.append("Model predictors: {}".format(", ".join(predictors) if predictors else "intercept only"))
    for metric in ("mean_latency", "p95_latency", "init_duration", "throughput"):
        selected = [
            (run, run["run_metrics"][metric])
            for run in usable
            if run["run_metrics"][metric] is not None
        ]
        if len(selected) <= rank:
            lines.append(
                "{}: unavailable ({} valid run observations; {} fitted parameters).".format(
                    RUN_METRIC_LABELS[metric], len(selected), rank
                )
            )
            continue
        response = np.asarray([value for _, value in selected], dtype=float)
        selected_matrix = np.column_stack(
            [
                np.ones(len(selected)),
            ]
            + [
                np.asarray(
                    [run["config"][field] for run, _ in selected], dtype=float
                )
                for field in ("containers", "agents", "message_size", "group_size")
                if any(
                    run["config"][field] != selected[0][0]["config"][field]
                    for run, _ in selected
                )
            ]
            + [
                np.asarray(
                    [
                        1.0 if run["config"][field] == category else 0.0
                        for run, _ in selected
                    ]
                )
                for field in ("platform", "workload")
                for category in sorted(set(run["config"][field] for run, _ in selected))[1:]
            ]
        )
        selected_rank = int(np.linalg.matrix_rank(selected_matrix))
        if selected_rank < selected_matrix.shape[1] or len(selected) <= selected_rank:
            lines.append(
                "{}: unavailable for valid rows (predictor matrix is rank-deficient "
                "or has no residual degrees of freedom).".format(
                    RUN_METRIC_LABELS[metric]
                )
            )
            continue

        coefficients, _, _, _ = np.linalg.lstsq(selected_matrix, response, rcond=None)
        predicted = selected_matrix.dot(coefficients)
        residuals = response - predicted
        sum_squared_error = float(np.sum(residuals ** 2))
        total_sum_squares = float(np.sum((response - np.mean(response)) ** 2))
        r_squared = (
            1.0 - sum_squared_error / total_sum_squares
            if total_sum_squares > 0
            else None
        )
        rmse = math.sqrt(sum_squared_error / len(response))
        residual_standard_error = math.sqrt(
            sum_squared_error / (len(response) - selected_rank)
        )
        lines.append(
            "{}: n={}, R_squared={}, RMSE={}, residual_SE={}, "
            "mean_residual={}, max_abs_residual={}".format(
                RUN_METRIC_LABELS[metric],
                len(response),
                format_value(r_squared),
                format_value(rmse),
                format_value(residual_standard_error),
                format_value(float(np.mean(residuals))),
                format_value(float(np.max(np.abs(residuals)))),
            )
        )
        for (run, observed), estimate, residual in zip(selected, predicted, residuals):
            lines.append(
                "  residual [{}]: observed={}, predicted={}, residual={}".format(
                    run["path"],
                    format_value(observed),
                    format_value(float(estimate)),
                    format_value(float(residual)),
                )
            )
    return lines


def write_group_report(runs, output_path):
    lines = [
        "Benchmark analysis",
        "Git commit: {}".format(runs[0]["commit"]),
        "Git worktree dirty: {}".format("yes" if runs[0]["worktree_dirty"] else "no"),
        "Input logs: {}".format(len(runs)),
        "Each input log is treated as one independent run. Message observations within a "
        "log are not treated as independent experimental replicates.",
        "",
        "Input files:",
    ]
    for run in runs:
        lines.append(
            "  {} | commit={} | config={}".format(
                run["path"], run["commit"], format_config(run["config"])
            )
        )
    commits = sorted(set(run["commit"] for run in runs))
    if len(commits) > 1:
        lines.extend(["", "WARNING: input analysis used logs from multiple Git commits."])
    lines.extend(_run_summary_lines(runs))
    lines.extend(_comparison_lines(runs))
    lines.extend(_scalability_lines(runs))
    lines.extend(_regression_lines(runs))
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def process_logs(log_paths, comparison_output=None):
    paths = [Path(path).expanduser().resolve() for path in log_paths]
    if not paths:
        raise ValueError("At least one log file is required.")
    if len(set(paths)) != len(paths):
        raise ValueError("The same log path was supplied more than once.")
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError("Log file does not exist: {}".format(path))

    commit, worktree_dirty = git_metadata()
    runs = [analyze_log(path, commit, worktree_dirty) for path in paths]
    for run in runs:
        output_path = write_run_report(run, independent_run_count(run, runs))
        print("Wrote {}".format(output_path))

    if len(runs) > 1 or comparison_output is not None:
        group_report = Path(comparison_output) if comparison_output else (
            Path.cwd() / "comparison_stats.txt"
        )
        write_group_report(runs, group_report)
        print("Wrote {}".format(group_report))

    csv_directory = (
        Path(comparison_output).parent
        if comparison_output is not None
        else (paths[0].parent if len(paths) == 1 else Path.cwd())
    )
    csv_path = csv_directory / "benchmark_results.csv"
    write_results_csv(runs, csv_path)
    print("Wrote {}".format(csv_path))
    return runs


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Analyze one log or multiple independent run logs. For replicated "
            "statistics, supply one log file per independent run."
        )
    )
    parser.add_argument(
        "logs",
        nargs="*",
        help="benchmark log file(s); defaults to out.txt",
    )
    args = parser.parse_args(argv)
    log_paths = args.logs or ["out.txt"]
    process_logs(log_paths)


if __name__ == "__main__":
    main()
