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

    def test_confidence_interval_requires_independent_replicates(self):
        self.assertEqual(process_res.mean_confidence_interval([3.0]), (None, None))
        low, high = process_res.mean_confidence_interval([1.0, 2.0, 3.0])
        self.assertLess(low, 2.0)
        self.assertGreater(high, 2.0)

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

        self.assertIn("Welch", report)
        self.assertIn("Holm_p", report)
        self.assertIn("efficiency=", report)
        self.assertIn("R_squared=", report)
        self.assertIn("residual [", report)

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
            process_res.process_logs(paths, comparison_path)

            self.assertTrue(
                (jade_directory / ("stats_{}.txt".format(paths[0].name))).is_file()
            )
            self.assertTrue(
                (jade_directory / ("histogram{}.png".format(paths[0].name))).is_file()
            )
            self.assertTrue(comparison_path.is_file())
            report = comparison_path.read_text(encoding="utf-8")
            self.assertIn("Git commit:", report)
            self.assertIn("need at least 2 per platform", report)
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
                temporary_directory, 1, 2, 1, 10, "inform", 1, 77
            )
            project = Path(temporary_directory) / "jason"
            self.assertIn("seed(77).", (project / "inform.asl").read_text(encoding="utf-8"))
            self.assertTrue((project / "myLib" / "timestamp.java").is_file())


if __name__ == "__main__":
    unittest.main()
