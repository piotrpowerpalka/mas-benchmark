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

1. Prepare an experiment configuration.
2. Generate the containerized deployment.
3. Start the benchmark environment.
4. Execute the workload.
5. Collect platform logs and Docker statistics.
6. Run the analysis scripts.
7. Export processed metrics and plots/tables.

### Example placeholder commands

```bash
# 1. Run experiment
 bash scripts/run-exp.sh <no-of-containers> <platform> <workload> <no-of-agents> <repeats> <message-size> <rebuild-docker> <group-size>

# 2. Analyze results
cd logs/logs_<platform>-c<no-of-containers>-n<no-of-agents>-r<repeats>-ms<message-size>-g<group-size>-m1GB-cpu1/
cat stats_logs_docker-compose-<platform>-c<no-of-containers>-n<no-of-agents>-r<repeats>-ms<message-size>-g<group-size>-m1GB-cpu1.yaml.log.txt
cat mem_stats_mem_docker-compose-<platform>-c<no-of-containers>-n<no-of-agents>-r<repeats>-ms<message-size>-g<group-size>-m1GB-cpu1.yaml.mas[0..containers]log.txt


```
---
## Limitations

Currently thera are several current limitations of the framework and evaluation scope:

- only two multi-agent platforms are compared [JADE/SPADE],
- only two SPADE XMPP backends are considered [Prosody/Tigase],
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

