# Containerized Evaluation Framework for Multi-Agent Platforms

<img width="1536" height="1024" alt="f98c2eb5-e938-408a-8fff-16dd56ceb49c" src="https://github.com/user-attachments/assets/007242d0-75f5-410e-8cc6-f08849518c50" />

A reproducible, containerized benchmarking framework for the quantitative evaluation of multi-agent platforms (MAPs) using **FIPA-inspired interaction protocol workloads**.

This project operationalizes three representative interaction patterns - **Inform**, **Query**, and **Contract Net Protocol (CNP)** - and evaluates platforms using a common set of communication, lifecycle, and resource-efficiency metrics. The framework is designed to improve **reproducibility**, **comparability**, and **extensibility** of experimental studies on multi-agent systems.

---

## Overview

Quantitative comparison of multi-agent platforms is often difficult because published experiments differ in workload design, infrastructure, measurement procedures, and runtime configuration. The framework described in the accompanying paper addresses this gap by combining:

- **explicit protocol-driven workloads**,
- **Docker-based execution environments**,
- **unified metric definitions**, and
- **scripted post-processing of experiment logs**.

The framework is demonstrated on a comparative study of:

- **JADE**
- **SPADE + Prosody**
- **SPADE + Tigase**
- **Jason on JADE infrastructure**

---

## Goals

The framework is built around five design goals:

- **Reproducibility** - experiments are defined through containerized deployment and explicit parameterization.
- **Comparability** - platforms are evaluated using shared workloads, measurement points, and reporting formats.
- **Extensibility** - new platforms, transports, and metrics can be added with limited changes.
- **Measurement validity** - repeated interactions, standardized logging, and consistent post-processing support systematic evaluation.
- **Practical usability** - experiments are executed through a unified runner workflow.

---

## Evaluated Workloads

The benchmark suite currently includes three FIPA-inspired workloads:

### 1. Inform
A one-way notification pattern stressing message dispatch, delivery latency, and sustained communication throughput.

### 2. Query
A request-response interaction pattern used to assess conversational overhead, end-to-end responsiveness, and round-trip behavior.

### 3. Contract Net Protocol (CNP)
A coordination- and negotiation-oriented workload that stresses multi-party interactions, message fan-out, and selection logic.

Together, these workloads cover a meaningful subset of communication patterns commonly encountered in multi-agent systems.

---

## Metrics

The framework defines a common metric set in three groups.

### Communication metrics
- Mean latency
- Jitter
- Mean throughput (messages/s)
- Mean throughput (bytes/s)
- Mean round-trip time (RTT) for Query workloads

### Agent and platform lifecycle metrics
- Platform readiness time
- Mean agent creation time

### Resource-efficiency metrics
- CPU utilization (p95)
- Peak memory consumption
- Estimated per-agent memory consumption

The framework derives these values from two main sources:

- **platform/application logs** generated during initialization and communication phases,
- **container resource logs** collected from Docker runtime statistics.

---

## Conceptual Architecture

At a high level, the framework consists of the following components:

- **Experiment runner** - orchestrates the full benchmark workflow.
- **Experiment generator** - prepares experiment-specific artifacts and configuration files.
- **Docker configuration generator** - creates the containerized deployment setup.
- **Data collector** - gathers application logs and Docker resource measurements.
- **Logs analyzer** - parses raw logs and computes quantitative metrics.

The experiment model is parameterized by:

- platform under test,
- transport/backend configuration,
- workload type,
- number of agents,
- number of containers/machines,
- number of repetitions,
- message size,
- CNP group size.

---

## Reproducibility

The framework is intended to support artifact-oriented experimentation by packaging execution environments, communication services, and measurement tooling into Docker-based deployments.

To make the repository fully reproducible in practice, the following artifacts should be version-controlled together:

- container build files,
- deployment descriptors,
- workload source code,
- experiment configuration files,
- runner scripts,
- log parsers,
- metric calculation scripts,
- raw or sample output datasets,
- documentation of the execution environment.

---


## Getting Started

### Python virtual environment

To keep the benchmark scripts and analysis tools reproducible, the project now includes a local virtual environment configuration.

1. Create the environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Use the helper script:

```bash
bash scripts/setup-venv.sh
```

This keeps all Python-based workloads and analysis scripts isolated from the global interpreter and makes the environment easy to recreate on any machine.

### Prerequisites

- Docker
- Docker Compose or another compatible container orchestration tool
- Python (for analysis scripts)
- Local virtual environment configured via `.venv`

### Typical workflow

The experiment runner is a Bash script. Run it from a Bash-compatible terminal. If you use WSL, create and activate the virtual environment inside WSL; a Windows `.venv` cannot be used by Linux Python.

The runner now resolves the repository root explicitly and passes absolute paths into the Python post-processing scripts. This avoids the `../../scripts` path breakage that happened when Bash was launched from PowerShell or from a nested logs directory.

1. Prepare an experiment configuration.
2. Generate the containerized deployment.
3. Start the benchmark environment.
4. Execute the workload.
5. Collect platform logs and Docker statistics.
6. Run the analysis scripts.
7. Export processed metrics and plots/tables.

Jason experiments can be started with the same runner, using `jason` as the
platform argument. Jason uses the JADE main container for distributed
communication:

```bash
bash scripts/run-exp.sh 2 jason inform 10 10 1024 false 3 100
```
The optional tenth argument sets the random seed; it defaults to
`213742189290` and is included in the experiment directory and log filenames:

```bash
bash scripts/run-exp.sh 2 jason inform 10 10 1024 false 3 100 42
```

### Example placeholder commands

```bash
# 1. Run experiment
 bash scripts/run-exp.sh <no-of-containers> <platform> <workload> <no-of-agents> <repeats> <message-size> <rebuild-docker> <group-size> <period-ms> <seed>

# 2. Analyze results
cd logs/logs_<platform>-c<containers>-n<agents>-r<repeats>-ms<size>-<workload>-g<group-size>-m1GB-cpu1-p<period>-seed<seed>/
cat stats_logs_docker-compose-<platform>-c<containers>-n<agents>-r<repeats>-ms<size>-<workload>-g<group-size>-m1GB-cpu1-p<period>-seed<seed>.yaml.log.txt
cat benchmark_results.csv

# 3. Analyze a group of experiment directories together
python3 ../../scripts/process_res_group.py ../logs_<platform>-c1-* ../logs_<platform>-c2-*

```

`process_res.py` accepts one log or multiple log paths. `process_res_group.py`
recursively finds `logs_docker-compose-*.yaml.log` in each supplied directory
(wildcard patterns are supported). Each input log is treated as one independent
run; retain separate log files for repeated runs of the same configuration.
The per-run report includes message and conversation latency in microseconds
and the current Git commit. A separate `benchmark_results.csv` contains the
requested per-run columns; its `where` value is the parent experiment-directory
name. Memory values are calculated across the run's available MAS and XMPP
Docker-stat logs: max is the maximum observed value and average is the pooled
sample mean. The CPU threshold is their pooled 95th percentile.
The `Shapiro-Wilk` CSV column contains the W statistic (blank when the test
cannot be computed).
For a single log the CSV is written beside that log; group analysis writes it
to the common parent directory of the input logs.
When multiple logs are supplied, `comparison_stats.txt` reports run-level
confidence intervals, matched-platform Welch tests with Holm correction,
one-container-baseline scalability efficiency, and guarded OLS diagnostics.
Insufficient replication or unmatched configurations are reported instead of
being treated as statistically significant.
New JADE and Jason logs record fractional-second timestamps. Existing logs
whose timestamps only contain whole seconds cannot provide microsecond
precision; converting their latency to microseconds does not restore that
missing precision.
---
## Limitations

Currently thera are several current limitations of the framework and evaluation scope:

- only three multi-agent platforms are compared [JADE/SPADE/Jason],
- only two SPADE XMPP backends are considered [Prosody/Tigase]; Jason uses JADE infrastructure,
- additional dimensions such as fault tolerance, long-running endurance, discovery-service performance, and migration-related metrics are outside the present scope.

---

## Future Work

Planned or recommended directions for further development include:

- adding more multi-agent platforms,
- extending the workload suite,
- including more failure-oriented and long-duration scenarios,
- expanding the metric set,
- improving the standardization of reproducible benchmarking artifacts.

## Recent project updates

- 2026-11-17: added a reproducible Python virtual environment setup (`.venv`, `requirements.txt`, and `scripts/setup-venv.sh`) to standardize local development and analysis runs.
- 2026-11-17: made `scripts/run-exp.sh` resolve project scripts and source files from the repository location, avoiding failures caused by relative Python script paths, and aligned memory-logger cleanup with the resolved path; documented the Bash and WSL virtual-environment requirements.

## License

**Apache-2.0**

