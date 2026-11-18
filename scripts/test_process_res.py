import tempfile
import unittest
from pathlib import Path

import process_res
import process_res_group


class ProcessResTests(unittest.TestCase):
    def test_parse_config_from_log_filename(self):
        path = Path(
            "logs_docker-compose-jason-c2-n10-r100-ms1024-inform-g3-m1GB-cpu1-p500.yaml.log"
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
            },
        )

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
        self.assertEqual(run["message_stats"]["mean"], 1.0)
        self.assertEqual(run["messages_lost"], 0)
        self.assertEqual(run["config"]["platform"], "jade")
        self.assertEqual(run["run_metrics"]["throughput"], 1.0)

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
            jade_directory = root / "logs_jade-c1-n2-r1-ms10-inform-g1-m1GB-cpu1"
            jason_directory = root / "logs_jason-c1-n2-r1-ms10-inform-g1-m1GB-cpu1"
            jade_directory.mkdir()
            jason_directory.mkdir()
            paths = []
            for directory, platform in (
                (jade_directory, "jade"),
                (jason_directory, "jason"),
            ):
                path = directory / (
                    "logs_docker-compose-{}-c1-n2-r1-ms10-inform-g1-m1GB-cpu1.yaml.log".format(
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


if __name__ == "__main__":
    unittest.main()
