import unittest
from unittest.mock import patch

from app.api import devops


def make_id(number):
    return f"{number:064x}"


def make_evidence(
    number,
    name,
    status="running",
    exit_code=0,
    health=None,
    restart_count=0,
    project="test-project",
    service=None,
):
    labels = {}
    if project:
        labels["com.docker.compose.project"] = project
    if service:
        labels["com.docker.compose.service"] = service

    return {
        "id": make_id(number),
        "container": name,
        "status": status,
        "health": health,
        "exit_code": exit_code,
        "restart_count": restart_count,
        "labels": labels,
        "collected_at": "2026-10-10T10:00:00+00:00",
    }


class TestContainerCorrelation(unittest.TestCase):
    def run_correlation(self, evidence_items):
        inventory = {
            "containers": [
                {
                    "id": item["id"],
                    "container": item["container"],
                    "status": item["status"],
                    "health": item["health"],
                    "exit_code": item["exit_code"],
                    "restart_count": item["restart_count"],
                    "collected_at": item["collected_at"],
                }
                for item in evidence_items
            ]
        }
        evidence_by_id = {
            item["id"]: item for item in evidence_items
        }

        def fake_fetch(path):
            if path == "/inventory":
                return inventory
            container_id = path.rsplit("/", 1)[-1]
            return evidence_by_id[container_id]

        with patch.object(
            devops, "fetch_collector_json", side_effect=fake_fetch
        ):
            return devops.correlate_container_evidence()

    def test_healthy_container_has_no_signals(self):
        healthy = make_evidence(1, "healthy-app")

        result = self.run_correlation([healthy])

        self.assertEqual(result["container_count"], 1)
        self.assertEqual(result["containers_with_signals"], 0)
        self.assertEqual(result["containers"][0]["severity"], "info")
        self.assertEqual(result["containers"][0]["signals"], [])

    def test_nonzero_exit_is_high_severity(self):
        failed = make_evidence(
            2, "failed-app", status="exited", exit_code=1
        )

        result = self.run_correlation([failed])
        record = result["containers"][0]

        self.assertEqual(record["severity"], "high")
        self.assertIn(
            "non_zero_exit",
            [signal["type"] for signal in record["signals"]],
        )

    def test_restart_count_raises_severity(self):
        restarting = make_evidence(3, "restarting-app", restart_count=3)

        result = self.run_correlation([restarting])
        record = result["containers"][0]

        self.assertEqual(record["severity"], "medium")
        self.assertIn(
            "restarts_observed",
            [signal["type"] for signal in record["signals"]],
        )

    def test_same_compose_project_is_contextual_relationship(self):
        failed = make_evidence(
            4, "failed-app", status="exited", exit_code=1,
            service="backend",
        )
        healthy = make_evidence(5, "healthy-app", service="frontend")

        result = self.run_correlation([failed, healthy])
        healthy_record = next(
            item for item in result["containers"]
            if item["container"] == "healthy-app"
        )

        self.assertEqual(len(healthy_record["possible_relationships"]), 1)
        relationship = healthy_record["possible_relationships"][0]
        self.assertEqual(relationship["relationship"], "same_compose_project")
        self.assertIn("does not establish", relationship["evidence"])


    def test_high_severity_is_not_downgraded_by_unknown_status(self):
        evidence = make_evidence(
            7, "unknown-unhealthy-app",
            status="created", health="unhealthy",
        )

        result = self.run_correlation([evidence])
        record = result["containers"][0]
        signal_types = [signal["type"] for signal in record["signals"]]

        self.assertEqual(record["severity"], "high")
        self.assertIn("unhealthy", signal_types)
        self.assertIn("unknown_status", signal_types)


    def test_signals_include_reason_and_evidence(self):
        evidence = make_evidence(
            8, "unhealthy-restarting-app",
            status="created", health="unhealthy", restart_count=3,
        )

        result = self.run_correlation([evidence])
        record = result["containers"][0]

        self.assertEqual(record["severity"], "high")
        self.assertGreaterEqual(len(record["signals"]), 3)

        for signal in record["signals"]:
            with self.subTest(signal=signal["type"]):
                self.assertTrue(signal.get("reason", "").strip())
                self.assertTrue(signal.get("evidence", "").strip())


    def test_evidence_reference_matches_container_snapshot(self):
        evidence = make_evidence(9, "reference-check-app")

        result = self.run_correlation([evidence])
        record = result["containers"][0]
        reference = record["evidence_ref"]

        self.assertEqual(reference["container_id"], evidence["id"])
        self.assertEqual(
            reference["collected_at"], evidence["collected_at"]
        )
        self.assertTrue(reference["source"])
        self.assertEqual(record["collected_at"], reference["collected_at"])

    def test_exit_and_unhealthy_signals_are_both_retained(self):
        failed_unhealthy = make_evidence(
            6, "failed-unhealthy-app",
            status="exited", exit_code=1, health="unhealthy",
        )

        result = self.run_correlation([failed_unhealthy])
        record = result["containers"][0]
        signal_types = [signal["type"] for signal in record["signals"]]

        self.assertIn("non_zero_exit", signal_types)
        self.assertIn("unhealthy", signal_types)


    def test_response_shape_contains_evidence_and_limitations(self):
        failed = make_evidence(
            10, "response-shape-app",
            status="exited", exit_code=1,
        )

        result = self.run_correlation([failed])
        record = result["containers"][0]

        self.assertEqual(
            result["correlation_type"], "deterministic_saved_evidence"
        )
        self.assertEqual(result["container_count"], 1)
        self.assertEqual(result["containers_with_signals"], 1)

        self.assertTrue(record["container"])
        self.assertTrue(record["container_id"])
        self.assertIn("severity", record)
        self.assertIn("collected_at", record)

        self.assertTrue(record["signals"])
        signal = record["signals"][0]
        self.assertTrue(signal["type"])
        self.assertTrue(signal["reason"])
        self.assertTrue(signal["evidence"])

        reference = record["evidence_ref"]
        self.assertEqual(reference["container_id"], failed["id"])
        self.assertEqual(
            reference["collected_at"], failed["collected_at"]
        )
        self.assertTrue(reference["source"])

        self.assertTrue(result["limitations"])
        self.assertTrue(
            any("causation" in item.lower()
                for item in result["limitations"])
        )

if __name__ == "__main__":
    unittest.main()
