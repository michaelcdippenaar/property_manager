"""Serializers for test_hub API — developer portal."""
from rest_framework import serializers
from apps.test_hub.models import TestRunRecord, TestIssue, TestHealthSnapshot, TestModuleSelfHealth


class TestRunRecordSerializer(serializers.ModelSerializer):
    pass_rate = serializers.ReadOnlyField()
    has_regressions = serializers.ReadOnlyField()

    class Meta:
        model = TestRunRecord
        fields = [
            "id", "module", "tier", "phase", "run_at", "triggered_by",
            "tests_run", "tests_passed", "tests_failed", "tests_xfailed",
            "tests_xpassed", "tests_skipped", "duration_seconds",
            "coverage_percent", "pass_rate", "has_regressions",
        ]


class TestIssueSerializer(serializers.ModelSerializer):
    days_open = serializers.ReadOnlyField()

    class Meta:
        model = TestIssue
        fields = [
            "id", "module", "title", "slug", "status", "discovered_at",
            "fixed_at", "test_file", "issue_file_path", "description",
            "root_cause", "days_open",
        ]


class TestHealthSnapshotSerializer(serializers.ModelSerializer):
    health_score = serializers.ReadOnlyField()

    class Meta:
        model = TestHealthSnapshot
        fields = [
            "id", "taken_at", "total_tests", "total_green", "total_red",
            "total_unit", "total_integration", "total_e2e",
            "open_issues", "fixed_issues", "avg_days_to_fix",
            "coverage_percent", "rag_last_indexed", "module_breakdown",
            "health_score",
        ]


class TestModuleSelfHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestModuleSelfHealth
        fields = "__all__"
