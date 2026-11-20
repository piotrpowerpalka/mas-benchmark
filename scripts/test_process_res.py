import ast
import csv
import tempfile
import unittest
from pathlib import Path

import process_res
import process_res_group
import gen_compose


class ProcessResTests(unittest.TestCase):
    def test_parse_config_from_log_filename(self):
        path = Path(
            "logs_docker-compose-jason-c2-n10-r100-ms1024-inform-g3-m1GB-cpu1-p500-seed123.yaml.log"
        )
        self.assertEqual(
            process_res.parse_config(path),
            {
                "platform": "jason",
                "containers": 2,
                "agents": 10,
                "repeats": 100,
                "message_size": 1024,
                "workload": "inform",
                "group_size": 3,
                "memory": "1GB",
                "cpus": 1.0,
                "period": 500,
                "seed": 123,
            },
        )

    def test_parse_config_preserves_legacy_names_without_seed(self):
        path = Path(
            "logs_docker-compose-jason-c2-n10-r100-ms1024-inform-g3-m1GB-cpu1-p500.yaml.log"
        )
        self.assertIsNone(process_res.parse_config(path)["seed"])

    def test_parse_config_accepts_uagents_platform(self):
        path = Path(
            "logs_docker-compose-uagents-c2-n5-r3-ms1024-cfp-g2-m1GB-cpu1-p250-seed77.yaml.log"
        )
        self.assertEqual(process_res.parse_config(path)["platform"], "uagents")

    def test_parse_config_accepts_uagents_agentverse_platform(self):
        path = Path(
            "logs_docker-compose-uagents-agentverse-c2-n2-r3-ms1024-cfp-g2-m1GB-cpu1-p250-seed77.yaml.log"
        )
        self.assertEqual(
            process_res.parse_config(path)["platform"], "uagents-agentverse"
        )

    def test_confidence_interval_requires_independent_replicates(self):
        self.assertEqual(process_res.mean_confidence_interval([3.0]), (None, None))
        low, high = process_res.mean_confidence_interval([1.0, 2.0, 3.0])
        self.assertLess(low, 2.0)
        self.assertGreater(high, 2.0)

    def test_independent_run_count_groups_seed_replicates_by_experiment(self):
        config = {
            "platform": "jade",
            "containers": 1,
            "agents": 2,
            "repeats": 1,
            "message_size": 10,
            "workload": "inform",
            "group_size": 1,
            "memory": "1GB",
            "cpus": 1.0,
            "period": None,
            "seed": 7,
        }
        run = {"config": config}
        seed_replicate = {"config": dict(config, seed=8)}
        other_platform = {"config": dict(config, platform="jason")}

        self.assertEqual(
            process_res.independent_run_count(
                run, [run, seed_replicate, other_platform]
            ),
            2,
        )
        self.assertEqual(
            process_res.independent_run_count({"config": None}, [run]), 1
        )

    def test_welch_test_and_holm_adjustment(self):
        result = process_res.welch_comparison([1.0, 2.0, 3.0], [5.0, 6.0, 7.0])
        self.assertIsNotNone(result)
        self.assertLess(result["ci_high"], 0)
        adjusted = process_res.holm_adjust([0.01, 0.04, 0.03])
        self.assertEqual(adjusted, [0.03, 0.06, 0.06])

    def test_analyze_log_parses_init_and_run_metrics(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / (
                "logs_docker-compose-jade-c1-n2-r1-ms10-inform-g1-m1GB-cpu1.yaml.log"
            )
            log_path.write_text(
                "\n".join(
                    [
                        "INFO | init;initializing;agent0;2025-01-01T10:00:00",
                        "INFO | init;running;agent0;2025-01-01T10:00:01",
                        "INFO | agent0;agent1;message;rw(1);cid(1);S;2025-01-01T10:00:02",
                        "INFO | agent0;agent1;message;rw(1);cid(1);R;2025-01-01T10:00:03",
                        "INFO | agent0;agent1;message;rw(2);cid(2);S;2025-01-01T10:00:04",
                        "INFO | agent0;agent1;message;rw(2);cid(2);R;2025-01-01T10:00:05",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            run = process_res.analyze_log(log_path, "test-commit", False)

        self.assertEqual(run["init_duration"], 1.0)
        self.assertEqual(run["message_stats"]["count"], 2)
        self.assertEqual(run["message_stats"]["mean"], 1_000_000.0)
        self.assertEqual(run["messages_lost"], 0)
        self.assertEqual(run["config"]["platform"], "jade")
        self.assertEqual(run["run_metrics"]["throughput"], 1.0)

    def test_latency_uses_microsecond_timestamp_precision(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / (
                "logs_docker-compose-jade-c1-n2-r1-ms10-inform-g1-m1GB-cpu1-seed5.yaml.log"
            )
            log_path.write_text(
                "\n".join(
                    [
                        "INFO | init;running;agent0;2025-01-01T10:00:00.000001",
                        "INFO | agent0;agent1;message;rw(1);cid(1);S;2025-01-01T10:00:00.123456",
                        "INFO | agent0;agent1;message;rw(1);cid(1);R;2025-01-01T10:00:00.123459",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            run = process_res.analyze_log(log_path, "test-commit", False)

        self.assertEqual(run["message_stats"]["mean"], 3.0)

    def test_analyze_uagents_log_format_and_uuid_identifiers(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / (
                "logs_docker-compose-uagents-c1-n2-r1-ms10-inform-g1-m1GB-cpu1-seed5.yaml.log"
            )
            log_path.write_text(
                "\n".join(
                    [
                        "mas0 | init;initializing;agent0;2025-01-01T10:00:00.000000",
                        "mas0 | init;running;agent0;2025-01-01T10:00:00.000001",
                        "mas0 | agent0;agent1;inform;rw-00000000-0000-0000-0000-000000000001;cid-00000000-0000-0000-0000-000000000002;S;2025-01-01T10:00:00.123456",
                        "mas0 | agent0;agent1;inform;rw-00000000-0000-0000-0000-000000000001;cid-00000000-0000-0000-0000-000000000002;R;2025-01-01T10:00:00.123956",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            run = process_res.analyze_log(log_path, "test-commit", False)

        self.assertEqual(run["config"]["platform"], "uagents")
        self.assertEqual(run["message_stats"]["count"], 1)
        self.assertEqual(run["message_stats"]["mean"], 500.0)
        self.assertEqual(run["messages_lost"], 0)

    def test_timestamp_parser_handles_quoted_and_epoch_microsecond_values(self):
        expected = process_res.pd.Timestamp("2025-01-01T10:00:00.123456")
        self.assertEqual(
            process_res.parse_timestamp('"2025-01-01T10:00:00.123456"'),
            expected,
        )
        self.assertEqual(
            process_res.parse_timestamp("1735725600123456"),
            process_res.pd.Timestamp(1735725600123456, unit="us"),
        )

    def test_histogram_is_written_for_empty_and_constant_samples(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            empty_path = root / "empty.png"
            constant_path = root / "constant.png"

            process_res.save_histogram([], empty_path, "Empty latency", "Latency [µs]", "blue")
            process_res.save_histogram(
                [5.0, 5.0, 5.0], constant_path, "Constant latency", "Latency [µs]", "orange"
            )

            for output_path in (empty_path, constant_path):
                self.assertTrue(output_path.is_file())
                self.assertGreater(output_path.stat().st_size, 8)
                self.assertEqual(output_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_group_collector_finds_logs_recursively(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "experiment-one"
            second = root / "experiment-two" / "nested"
            first.mkdir()
            second.mkdir(parents=True)
            first_log = first / "logs_docker-compose-jade-c1-n2-r1-ms10-inform-g1-m1GB-cpu1.yaml.log"
            second_log = second / "logs_docker-compose-jason-c1-n2-r1-ms10-inform-g1-m1GB-cpu1.yaml.log"
            (first / "mem_docker-compose-jade.log").touch()
            first_log.touch()
            second_log.touch()

            logs = process_res_group.collect_logs(
                [str(root / "experiment-one"), str(root / "experiment-two")]
            )

        self.assertEqual(logs, [first_log.resolve(), second_log.resolve()])

    def test_group_report_includes_inference_scalability_and_regression(self):
        runs = []
        for platform in ("jade", "jason"):
            for containers in (1, 2):
                for replicate in (1, 2):
                    config = {
                        "platform": platform,
                        "containers": containers,
                        "agents": 10,
                        "repeats": 5,
                        "message_size": 1024,
                        "workload": "inform",
                        "group_size": 2,
                        "memory": "1GB",
                        "cpus": 1.0,
                        "period": None,
                        "seed": 77,
                    }
                    factor = 1.0 if platform == "jade" else 1.5
                    runs.append(
                        {
                            "path": Path("run-{}-{}-{}.log".format(platform, containers, replicate)),
                            "commit": "test-commit",
                            "worktree_dirty": False,
                            "config": config,
                            "run_metrics": {
                                "mean_latency": factor * containers + replicate * 0.1,
                                "p95_latency": factor * containers + replicate * 0.2,
                                "init_duration": factor + replicate * 0.1,
                                "throughput": 100.0 * containers / factor + replicate,
                                "message_loss_rate": replicate * 0.001,
                            },
                        }
                    )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "comparison_stats.txt"
            process_res.write_group_report(runs, output_path)
            report = output_path.read_text(encoding="utf-8")

        self.assertIn("Kruskal-Wallis", report)
        self.assertIn("Mann-Whitney U", report)
        self.assertIn("Holm_p", report)
        self.assertIn("efficiency=", report)
        self.assertIn("R_squared=", report)
        self.assertIn("residual [", report)

    def test_group_report_aggregates_seeds_and_tests_all_metrics(self):
        runs = []
        for platform, baseline in (("jade", 1.0), ("uagents", 101.0)):
            for replicate, seed in enumerate(range(11, 21)):
                config = {
                    "platform": platform,
                    "containers": 2,
                    "agents": 10,
                    "repeats": 5,
                    "message_size": 1024,
                    "workload": "inform",
                    "group_size": 2,
                    "memory": "1GB",
                    "cpus": 1.0,
                    "period": 500,
                    "seed": seed,
                }
                metrics = {
                    metric: baseline + replicate
                    for metric in process_res.RUN_METRICS
                }
                runs.append(
                    {
                        "path": Path("run-{}-seed{}.log".format(platform, seed)),
                        "commit": "test-commit",
                        "worktree_dirty": False,
                        "config": config,
                        "run_metrics": metrics,
                    }
                )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "comparison_stats.txt"
            process_res.write_group_report(runs, output_path)
            report = output_path.read_text(encoding="utf-8")

        jade_configuration = next(
            line for line in report.splitlines()
            if line.startswith("Configuration: platform=jade")
        )
        self.assertNotIn("seed=", jade_configuration)
        self.assertIn(
            "independent_runs=10, seeds=11, 12, 13, 14, 15, 16, 17, 18, 19, 20",
            report,
        )
        self.assertIn("mean_latency [µs]: n_runs=10", report)
        self.assertIn("median=5.5", report)
        self.assertIn("max_memory [MiB]: n_runs=10", report)
        self.assertIn("CPU_p95_threshold [%]: n_runs=10", report)
        self.assertIn("Kruskal-Wallis / mean_latency [µs]", report)
        self.assertIn("Mann-Whitney U / jade vs uagents", report)
        self.assertIn("adjusted p < 0.05", report)

    def test_process_logs_writes_reports_and_commit_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            jade_directory = root / "logs_jade-c1-n2-r1-ms10-inform-g1-m1GB-cpu1-seed7"
            jason_directory = root / "logs_jason-c1-n2-r1-ms10-inform-g1-m1GB-cpu1-seed7"
            jade_directory.mkdir()
            jason_directory.mkdir()
            paths = []
            for directory, platform in (
                (jade_directory, "jade"),
                (jason_directory, "jason"),
            ):
                path = directory / (
                    "logs_docker-compose-{}-c1-n2-r1-ms10-inform-g1-m1GB-cpu1-seed7.yaml.log".format(
                        platform
                    )
                )
                path.write_text(
                    "\n".join(
                        [
                            "INFO | init;initializing;agent0;2025-01-01T10:00:00",
                            "INFO | init;running;agent0;2025-01-01T10:00:01",
                            "INFO | agent0;agent1;message;rw(1);cid(1);S;2025-01-01T10:00:02",
                            "INFO | agent0;agent1;message;rw(1);cid(1);R;2025-01-01T10:00:03",
                            "INFO | agent0;agent1;message;rw(2);cid(2);S;2025-01-01T10:00:04",
                            "INFO | agent0;agent1;message;rw(2);cid(2);R;2025-01-01T10:00:05",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )
                paths.append(path)

            memory_log = jade_directory / (
                "mem_{}-mas0.log".format(paths[0].name[len("logs_") : -len(".log")])
            )
            memory_log.write_text(
                "\n".join(
                    [
                        "1;mas0;32.00MiB / 512MiB;5.00%",
                        "2;mas0;40.00MiB / 512MiB;50.00%",
                        "3;mas0;60.00MiB / 512MiB;95.00%",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            comparison_path = root / "comparison_stats.txt"
            process_res_group.main([str(root)])

            self.assertTrue(
                (jade_directory / ("stats_{}.txt".format(paths[0].name))).is_file()
            )
            for path in paths:
                report_path = path.parent / ("stats_{}.txt".format(path.name))
                report = report_path.read_text(encoding="utf-8")
                self.assertIn("Independent log runs supplied: 1", report)
                self.assertIn(
                    "Run-level confidence intervals and significance tests: unavailable",
                    report,
                )
            self.assertTrue(
                (jade_directory / ("histogram{}.png".format(paths[0].name))).is_file()
            )
            self.assertTrue(comparison_path.is_file())
            report = comparison_path.read_text(encoding="utf-8")
            self.assertIn("Git commit:", report)
            self.assertIn("need at least 2 independent runs per platform", report)
            csv_path = root / "benchmark_results.csv"
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, list(process_res.CSV_FIELDS))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["seed"], "7")
            self.assertEqual(rows[0]["where"], jade_directory.name)
            self.assertEqual(rows[0]["latency [µs]"], "1000000.0")
            self.assertEqual(rows[0]["Max memory [MiB]"], "60.0")
            self.assertEqual(rows[0]["Avg memory [MiB]"], "44.0")
            self.assertEqual(rows[0]["CPU in top 5% [threshold %]"], "90.5")

    def test_seed_is_applied_to_generated_compose_and_jason_files(self):
        compose = gen_compose.gen_compose(
            "jade", 1, 2, 1, 10, "inform", 1, seed=77
        )
        self.assertIn("--seed 77", compose)
        spade_compose = gen_compose.gen_compose(
            "prosody", 1, 2, 1, 10, "inform", 1, seed=88
        )
        self.assertIn("--seed 88", spade_compose)
        jason_compose = gen_compose.gen_compose(
            "jason", 1, 2, 1, 10, "inform", 1, seed=99
        )
        self.assertIn("mas0:", jason_compose)

        with tempfile.TemporaryDirectory() as temporary_directory:
            gen_compose._write_jason_project(
                temporary_directory, 1, 2, 1, 10, "inform", 1, 77, 250
            )
            project = Path(temporary_directory) / "jason"
            inform = (project / "inform.asl").read_text(encoding="utf-8")
            self.assertIn("seed(77).", inform)
            self.assertIn("period_ms(250).", inform)
            self.assertIn(".wait(P);", inform)
            self.assertIn(".myLib.random_payload(Sz, S, Me, Sequence, Payload);", inform)
            self.assertTrue((project / "myLib" / "random_payload.java").is_file())
            self.assertTrue((project / "myLib" / "timestamp.java").is_file())

    def test_uagents_compose_uses_agents_without_a_server_container(self):
        compose = gen_compose.gen_compose(
            "uagents",
            2,
            5,
            3,
            1024,
            "cfp",
            2,
            seed=77,
            period=250,
        )

        self.assertIn("mas0:", compose)
        self.assertIn("mas1:", compose)
        self.assertIn("dockerfile: Dockerfile.uagents", compose)
        self.assertIn('- "5"', compose)
        self.assertIn("- cfp", compose)
        self.assertIn("- local", compose)
        self.assertIn('- "77"', compose)
        self.assertNotIn("serverhello", compose)

    def test_uagents_agentverse_compose_uses_mailbox_transport(self):
        compose = gen_compose.gen_compose(
            "uagents-agentverse",
            2,
            2,
            3,
            1024,
            "cfp",
            2,
            seed=77,
            period=250,
        )

        self.assertIn("- agentverse", compose)
        self.assertIn(
            'AGENTVERSE_API_TOKEN: "${AGENTVERSE_API_TOKEN:?Set AGENTVERSE_API_TOKEN}"',
            compose,
        )
        self.assertIn('AGENTVERSE_TEAM: "${AGENTVERSE_TEAM:-}"', compose)
        self.assertNotIn("serverhello", compose)

    def test_uagents_agentverse_supports_multiple_agents_per_container(self):
        compose = gen_compose.gen_compose(
            "uagents-agentverse", 2, 10, 1, 10, "inform", 1
        )

        self.assertIn("- agentverse", compose)
        self.assertIn('- "10"', compose)

    def test_uagents_workloads_are_separate_agent_classes(self):
        source_dir = Path(__file__).resolve().parents[1] / "src" / "uagents"
        workload_classes = (
            ("informAgent.py", "InformAgent"),
            ("queryAgent.py", "QueryAgent"),
            ("cfpAgent.py", "CfpAgent"),
        )

        for filename, class_name in workload_classes:
            tree = ast.parse((source_dir / filename).read_text(encoding="utf-8"))
            class_definitions = [
                node for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
            ]
            self.assertEqual(len(class_definitions), 1)
            self.assertTrue(
                any(
                    isinstance(base, ast.Name) and base.id == "BenchmarkAgent"
                    for base in class_definitions[0].bases
                )
            )

    def test_uagents_compose_requires_an_agent_per_container(self):
        with self.assertRaisesRegex(ValueError, "at least one agent per container"):
            gen_compose.gen_compose("uagents", 3, 2, 1, 10, "inform", 1)

    def test_uagents_compose_requires_multiple_agents_and_known_workloads(self):
        with self.assertRaisesRegex(ValueError, "at least two agents"):
            gen_compose.gen_compose("uagents", 1, 1, 1, 10, "inform", 1)
        with self.assertRaisesRegex(ValueError, "Unsupported uAgents workload"):
            gen_compose.gen_compose("uagents", 1, 2, 1, 10, "unknown", 1)

    def test_jason_period_is_applied_to_all_workloads(self):
        for workload in ("inform", "query", "cfp"):
            with tempfile.TemporaryDirectory() as temporary_directory:
                gen_compose._write_jason_project(
                    temporary_directory,
                    1,
                    2,
                    3,
                    10,
                    workload,
                    1,
                    77,
                    250,
                )
                project = Path(temporary_directory) / "jason"
                agent_source = (project / "{}.asl".format(workload)).read_text(
                    encoding="utf-8"
                )

            self.assertIn("period_ms(250).", agent_source)
            self.assertIn(".wait(P);", agent_source)

    def test_jason_logs_use_uuid_prefixed_ids_for_all_workloads(self):
        for workload in ("inform", "query", "cfp"):
            with tempfile.TemporaryDirectory() as temporary_directory:
                gen_compose._write_jason_project(
                    temporary_directory,
                    1,
                    2,
                    3,
                    10,
                    workload,
                    1,
                    77,
                    250,
                )
                project = Path(temporary_directory) / "jason"
                agent_source = (project / "{}.asl".format(workload)).read_text(
                    encoding="utf-8"
                )
                init_source = (project / "init.asl").read_text(encoding="utf-8")

            for source in (agent_source, init_source):
                self.assertIn('.concat("rw-",', source)
                self.assertIn('.concat("cid-",', source)
                self.assertNotRegex(
                    source,
                    r"(?m)^\s*(?:Rw|ReplyRw|Cid)\s*=\s*(?:rw|cid)\(",
                )
            self.assertIn("+start(Rw, Cid)[source(A)]", agent_source)
            self.assertIn(".send(A, signal, start(Rw, Cid));", init_source)


if __name__ == "__main__":
    unittest.main()
