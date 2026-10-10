import unittest

from app.api.devops import assess_container_evidence


def make_assessment_evidence(**overrides):
    evidence = {
        "id": "a" * 64,
        "container": "assessment-test",
        "status": "running",
        "exit_code": 0,
        "health": "healthy",
        "restart_count": 0,
        "metrics": {},
        "logs": "",
        "collected_at": "2026-10-10T10:00:00+00:00",
        "evidence_source": "test_snapshot",
    }
    evidence.update(overrides)
    return evidence


class TestContainerAssessment(unittest.TestCase):
    def test_healthy_container_preserves_existing_response_fields(self):
        result = assess_container_evidence(make_assessment_evidence())

        for field in (
            "assessment_type",
            "severity",
            "findings",
            "diagnosis",
            "observations",
            "recommendations",
            "confidence",
            "evidence_collected_at",
            "limitations",
        ):
            with self.subTest(field=field):
                self.assertIn(field, result)

        self.assertEqual(result["findings"], [])
        self.assertEqual(result["finding_details"], [])

    def test_nonzero_exit_has_reason_evidence_and_snapshot_reference(self):
        evidence = make_assessment_evidence(
            status="exited",
            exit_code=1,
            health=None,
        )

        result = assess_container_evidence(evidence)
        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "non_zero_exit"
        )

        self.assertIn("non_zero_exit", result["findings"])
        self.assertTrue(detail["reason"])
        self.assertTrue(detail["evidence"])
        self.assertTrue(any("exit code is 1" in item for item in detail["evidence"]))
        self.assertEqual(
            detail["evidence_ref"]["collected_at"],
            evidence["collected_at"],
        )
        self.assertEqual(detail["evidence_ref"]["source"], "test_snapshot")

    def test_missing_exit_code_has_specific_evidence(self):
        result = assess_container_evidence(
            make_assessment_evidence(
                status="exited",
                exit_code=None,
                health=None,
            )
        )

        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "exited_without_exit_code"
        )
        self.assertTrue(
            any("without a recorded exit code" in item.lower()
                for item in detail["evidence"])
        )

    def test_high_memory_finding_uses_high_threshold(self):
        result = assess_container_evidence(
            make_assessment_evidence(metrics={"memory_percent": 95.5})
        )

        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "high_memory_usage"
        )
        self.assertIn("90%", detail["reason"])
        self.assertTrue(
            any("95.5%" in item for item in detail["evidence"])
        )

    def test_elevated_memory_finding_uses_elevated_threshold(self):
        result = assess_container_evidence(
            make_assessment_evidence(metrics={"memory_percent": 85.0})
        )

        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "elevated_memory_usage"
        )
        self.assertIn("80%", detail["reason"])
        self.assertTrue(
            any("85.0%" in item for item in detail["evidence"])
        )
        self.assertNotIn("high_memory_usage", result["findings"])

    def test_simulated_database_failure_is_clearly_qualified(self):
        result = assess_container_evidence(
            make_assessment_evidence(
                status="exited",
                exit_code=1,
                health=None,
                logs="ERROR: simulated database connection failure",
            )
        )

        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "known_simulated_database_failure"
        )
        combined = " ".join([detail["reason"], *detail["evidence"]]).lower()
        self.assertIn("not proof", combined)
        self.assertIn("real database outage", combined)

    def test_each_finding_detail_has_required_shape(self):
        result = assess_container_evidence(
            make_assessment_evidence(
                health="unhealthy",
                restart_count=3,
                logs="ERROR: example application failure",
            )
        )

        self.assertTrue(result["finding_details"])
        for detail in result["finding_details"]:
            with self.subTest(finding=detail["finding"]):
                self.assertIn(detail["finding"], result["findings"])
                self.assertTrue(detail["reason"].strip())
                self.assertTrue(detail["evidence"])
                self.assertIn("collected_at", detail["evidence_ref"])
                self.assertIn("source", detail["evidence_ref"])

    def test_custom_evidence_source_is_preserved(self):
        result = assess_container_evidence(
            make_assessment_evidence(
                health="unhealthy",
                evidence_source="collector_snapshot_v2",
            )
        )

        detail = next(
            item for item in result["finding_details"]
            if item["finding"] == "health_unhealthy"
        )
        self.assertEqual(
            detail["evidence_ref"]["source"],
            "collector_snapshot_v2",
        )


if __name__ == "__main__":
    unittest.main()
