"""Tests for benchmarks.metrics — metric computation and reporting."""

import pytest

from benchmarks.metrics import (
    BenchmarkMetrics,
    Prediction,
    compute_metrics,
    render_markdown_report,
)


def _make_predictions(pairs: list[tuple[int, int]]) -> list[Prediction]:
    """Helper: create Prediction objects from (actual, predicted) pairs."""
    return [
        Prediction(
            case_id=f"case_{i}",
            actual_esi=actual,
            predicted_esi=predicted,
            chief_complaint=f"complaint_{i}",
        )
        for i, (actual, predicted) in enumerate(pairs)
    ]


class TestComputeMetrics:
    def test_perfect_predictions(self):
        """All exact matches -> 100% accuracy, 0 errors."""
        preds = _make_predictions([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
        m = compute_metrics(preds)
        assert m.total == 5
        assert m.exact_match == 5
        assert m.exact_match_rate == 1.0
        assert m.within_one == 5
        assert m.under_triage == 0
        assert m.over_triage == 0
        assert m.critical_under_triage == 0

    def test_all_critical_under_triage(self):
        """Worst case: all ESI 1/2 patients assigned ESI 5."""
        preds = _make_predictions([(1, 5), (2, 5), (1, 3), (2, 4)])
        m = compute_metrics(preds)
        assert m.critical_under_triage == 4
        assert m.critical_under_triage_rate == 1.0
        assert m.exact_match == 0
        assert len(m.critical_under_triage_cases) == 4

    def test_mixed_results(self):
        preds = _make_predictions([
            (1, 1),  # exact match
            (2, 3),  # critical under-triage
            (3, 2),  # over-triage
            (4, 5),  # under-triage (not critical)
            (5, 5),  # exact match
        ])
        m = compute_metrics(preds)
        assert m.total == 5
        assert m.exact_match == 2
        assert m.critical_under_triage == 1
        assert m.under_triage == 2  # (2->3) and (4->5)
        assert m.over_triage == 1  # (3->2)
        assert m.within_one == 5  # (1,1)=exact, (2,3)=+1, (3,2)=-1, (4,5)=+1, (5,5)=exact

    def test_confusion_matrix(self):
        preds = _make_predictions([(1, 1), (1, 2), (2, 1)])
        m = compute_metrics(preds)
        assert m.confusion[1][1] == 1
        assert m.confusion[1][2] == 1
        assert m.confusion[2][1] == 1

    def test_per_class_recall(self):
        preds = _make_predictions([(1, 1), (1, 2), (2, 2)])
        m = compute_metrics(preds)
        assert m.per_class_recall(1) == 0.5  # 1/2 ESI-1 correct
        assert m.per_class_recall(2) == 1.0  # 1/1 ESI-2 correct
        assert m.per_class_recall(3) == 0.0  # no ESI-3 cases

    def test_empty_predictions_raises(self):
        with pytest.raises(ValueError, match="empty"):
            compute_metrics([])

    def test_to_dict_serializable(self):
        """Ensure to_dict() produces JSON-serializable output."""
        import json
        preds = _make_predictions([(1, 2), (3, 3)])
        m = compute_metrics(preds)
        d = m.to_dict()
        # Should not raise
        json.dumps(d)
        assert d["total"] == 2
        assert d["critical_under_triage"] == 1


class TestRenderMarkdownReport:
    def test_contains_key_sections(self):
        preds = _make_predictions([(1, 1), (2, 3), (3, 3)])
        m = compute_metrics(preds)
        report = render_markdown_report(m, title="Test Report")
        assert "# Test Report" in report
        assert "Summary Metrics" in report
        assert "Per-Class Recall" in report
        assert "Confusion Matrix" in report
        assert "SAFETY GATE" in report

    def test_safety_gate_passed(self):
        preds = _make_predictions([(1, 1), (2, 2)])
        m = compute_metrics(preds)
        report = render_markdown_report(m)
        assert "PASSED" in report

    def test_safety_gate_failed(self):
        preds = _make_predictions([(1, 3)])
        m = compute_metrics(preds)
        report = render_markdown_report(m)
        assert "FAILED" in report
        assert "Critical Under-Triage Cases" in report
