import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from app.api.devops import get_observability_capabilities


def fake_response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def inventory(collected_at):
    return {
        "collected_at": collected_at,
        "total_discovered": 3,
        "total_collected": 3,
        "total_failed": 0,
    }


def host_evidence(collected_at):
    return {"collected_at": collected_at}


class TestObservabilityCapabilities(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.fresh = self.now.isoformat()
        self.old = (self.now - timedelta(minutes=45)).isoformat()
        self.env = patch.dict(
            os.environ,
            {
                "LUMORA_PROMETHEUS_URL": "",
                "LUMORA_LOKI_URL": "",
                "LUMORA_OTEL_ENDPOINT": "",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("app.api.devops.requests.get")
    def test_fresh_native_evidence_and_unconfigured_integrations(self, get):
        get.side_effect = [
            fake_response({"status": "healthy"}),
            fake_response(inventory(self.fresh)),
            fake_response(host_evidence(self.fresh)),
        ]

        result = get_observability_capabilities()

        self.assertEqual(result["collector"]["status"], "available")
        self.assertEqual(result["sources"]["docker_inventory"]["status"], "available")
        self.assertEqual(result["sources"]["host_ssh_kernel"]["status"], "available")
        self.assertEqual(
            result["sources"]["docker_inventory"]["total_collected"], 3
        )
        for integration in ("prometheus", "loki", "opentelemetry"):
            with self.subTest(integration=integration):
                self.assertEqual(
                    result["integrations"][integration]["status"],
                    "not_configured",
                )
                self.assertFalse(
                    result["integrations"][integration]["connection_verified"]
                )

    @patch("app.api.devops.requests.get")
    def test_old_evidence_is_marked_stale(self, get):
        get.side_effect = [
            fake_response({"status": "healthy"}),
            fake_response(inventory(self.old)),
            fake_response(host_evidence(self.old)),
        ]

        result = get_observability_capabilities()

        self.assertEqual(result["sources"]["docker_inventory"]["status"], "stale")
        self.assertEqual(result["sources"]["host_ssh_kernel"]["status"], "stale")

    @patch("app.api.devops.requests.get")
    def test_unreachable_collector_is_reported_without_raising(self, get):
        import requests

        get.side_effect = requests.ConnectionError("private test detail")

        result = get_observability_capabilities()

        self.assertEqual(result["collector"]["status"], "unavailable")
        self.assertEqual(
            result["sources"]["docker_inventory"]["status"], "unavailable"
        )
        self.assertEqual(
            result["sources"]["host_ssh_kernel"]["status"], "unavailable"
        )
        serialized = str(result)
        self.assertNotIn("private test detail", serialized)

    @patch("app.api.devops.requests.get")
    def test_missing_timestamp_is_unavailable(self, get):
        get.side_effect = [
            fake_response({"status": "healthy"}),
            fake_response(inventory(None)),
            fake_response(host_evidence(None)),
        ]

        result = get_observability_capabilities()

        self.assertEqual(
            result["sources"]["docker_inventory"]["status"], "unavailable"
        )
        self.assertEqual(
            result["sources"]["host_ssh_kernel"]["status"], "unavailable"
        )

    @patch("app.api.devops.requests.get")
    def test_configured_endpoint_is_not_claimed_as_verified(self, get):
        os.environ["LUMORA_PROMETHEUS_URL"] = "http://example.invalid"
        get.side_effect = [
            fake_response({"status": "healthy"}),
            fake_response(inventory(self.fresh)),
            fake_response(host_evidence(self.fresh)),
        ]

        result = get_observability_capabilities()

        self.assertEqual(
            result["integrations"]["prometheus"]["status"], "configured"
        )
        self.assertFalse(
            result["integrations"]["prometheus"]["connection_verified"]
        )


if __name__ == "__main__":
    unittest.main()
