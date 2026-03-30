"""Tests for benchmarks.mietic_loader — dataset loading and validation."""

import csv
import os
import tempfile

import pytest

from benchmarks.mietic_loader import (
    MIETICCorpusEntry,
    MIETICSchemaError,
    MIETICValidatedCase,
    _parse_esi_band,
    _safe_float,
    _safe_int,
    _strip_bom_from_columns,
    corpus_summary,
    load_mietic_corpus,
    load_mietic_validated,
    validated_summary,
)


# ---------------------------------------------------------------------------
# _strip_bom_from_columns
# ---------------------------------------------------------------------------

class TestStripBomFromColumns:
    def test_strips_chinese_bom_artifact(self):
        cols = ["\u9518\u7e2eubject_id", "stay_id", "acuity"]
        cleaned = _strip_bom_from_columns(cols)
        assert cleaned[0] == "subject_id"  # restored from corrupted 锘縮ubject_id
        assert cleaned[1] == "stay_id"

    def test_strips_standard_bom(self):
        cols = ["\ufeffsubject_id", "stay_id"]
        cleaned = _strip_bom_from_columns(cols)
        assert cleaned[0] == "subject_id"

    def test_no_bom_passthrough(self):
        cols = ["subject_id", "stay_id"]
        cleaned = _strip_bom_from_columns(cols)
        assert cleaned == cols

    def test_empty_list(self):
        assert _strip_bom_from_columns([]) == []


# ---------------------------------------------------------------------------
# _parse_esi_band
# ---------------------------------------------------------------------------

class TestParseEsiBand:
    def test_esi1(self):
        instr = "Analyze the patient's condition and assess if they require immediate life-saving interventions."
        assert _parse_esi_band(instr) == "1"

    def test_esi2(self):
        instr = "Determine if the patient meets ESI Level 2 criteria by assessing for high-risk situations."
        assert _parse_esi_band(instr) == "2"

    def test_esi3_5(self):
        instr = "Predict the number of resources likely required for their ED visit."
        assert _parse_esi_band(instr) == "3-5"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Cannot determine ESI band"):
            _parse_esi_band("Some random instruction text")


# ---------------------------------------------------------------------------
# _safe_float / _safe_int
# ---------------------------------------------------------------------------

class TestSafeParsers:
    def test_safe_float_valid(self):
        assert _safe_float("97.8") == 97.8
        assert _safe_float("68.0") == 68.0

    def test_safe_float_empty(self):
        assert _safe_float("") is None
        assert _safe_float("  ") is None
        assert _safe_float(None) is None

    def test_safe_float_invalid(self):
        assert _safe_float("Critical") is None
        assert _safe_float("uta") is None

    def test_safe_int_valid(self):
        assert _safe_int("42") == 42
        assert _safe_int("1.0") == 1  # handles float-formatted ints

    def test_safe_int_empty(self):
        assert _safe_int("") == 0
        assert _safe_int("", default=99) == 99

    def test_safe_int_invalid(self):
        assert _safe_int("abc") == 0


# ---------------------------------------------------------------------------
# load_mietic_corpus (with temp CSV)
# ---------------------------------------------------------------------------

class TestLoadMieticCorpus:
    def _write_corpus(self, tmpdir, rows):
        path = os.path.join(tmpdir, "MIETIC.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["instruction", "input", "output"])
            for row in rows:
                writer.writerow(row)
        return tmpdir

    def test_loads_esi1_and_esi2(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_corpus(td, [
                [
                    "Assess if they require immediate life-saving interventions.",
                    "A 70-year-old male with cardiac arrest.",
                    "Patient needs resuscitation.",
                ],
                [
                    "Determine if patient meets ESI Level 2 criteria.",
                    "A 50-year-old female with chest pain.",
                    "Patient meets ESI 2.",
                ],
            ])
            entries = load_mietic_corpus(td)
            assert len(entries) == 2
            assert entries[0].esi_band == "1"
            assert entries[1].esi_band == "2"

    def test_limit_parameter(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_corpus(td, [
                ["immediate life-saving interventions", "input1", "output1"],
                ["ESI Level 2 criteria", "input2", "output2"],
                ["resources likely required", "input3", "output3"],
            ])
            entries = load_mietic_corpus(td, limit=2)
            assert len(entries) == 2

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError):
                load_mietic_corpus(td)

    def test_bad_schema_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "MIETIC.csv")
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["wrong_col1", "wrong_col2"])
                writer.writerow(["a", "b"])
            with pytest.raises(MIETICSchemaError, match="missing columns"):
                load_mietic_corpus(td)

    def test_empty_corpus_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "MIETIC.csv")
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["instruction", "input", "output"])
                # Only the meta "instruction" row, which is skipped
                writer.writerow(["instruction", "input", "output"])
            with pytest.raises(MIETICSchemaError, match="No valid entries"):
                load_mietic_corpus(td)

    def test_corpus_summary(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_corpus(td, [
                ["immediate life-saving interventions", "i", "o"],
                ["ESI Level 2 criteria", "i", "o"],
                ["resources likely required", "i", "o"],
                ["resources likely required", "i", "o"],
            ])
            entries = load_mietic_corpus(td)
            s = corpus_summary(entries)
            assert s["total"] == 4
            assert s["esi_1"] == 1
            assert s["esi_2"] == 1
            assert s["esi_3_5"] == 2


# ---------------------------------------------------------------------------
# load_mietic_validated (with temp CSV)
# ---------------------------------------------------------------------------

class TestLoadMieticValidated:
    HEADERS = [
        "subject_id", "stay_id", "hadm_id", "intime", "outtime",
        "gender", "race", "arrival_transport", "disposition",
        "temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp",
        "pain", "acuity", "chiefcomplaint",
        "invasive_ventilation", "invasive_ventilation_beyond_1h",
        "non_invasive_ventilation",
        "transfer2surgeryin1h", "transfer_to_surgery_beyond_1h",
        "transfer_to_icu_in_1h", "transfer_to_icu_beyond_1h",
        "transfer_within_1h", "transfer_beyond_1h",
        "expired_within_1h", "expired_beyond_1h",
        "tier1_med_usage_1h", "tier1_med_usage_beyond_1h",
        "tier2_med_usage", "tier3_med_usage", "tier4_med_usage",
        "psychotropic_med_within_120min",
        "transfusion_within_1h", "transfusion_beyond_1h",
        "red_cell_order_more_than_1", "intraosseous_line_placed",
        "critical_procedure",
        "lab_event_count", "microbio_event_count", "exam_count",
        "intravenous_fluids", "intravenous", "intramuscular",
        "nebulized_medications", "oral_medications",
        "consults_count", "procedure_count",
        "age", "resources_used", "tiragecase",
        "Expert 1 Opinion", "Expert 2 Opinion", "Expert 3 Opinion",
        "Final Decision",
    ]

    def _make_row(self, acuity=2, decision="RETAIN", gender="M", age="55.0"):
        """Build a minimal valid row."""
        row = [""] * len(self.HEADERS)
        idx = {h: i for i, h in enumerate(self.HEADERS)}
        row[idx["subject_id"]] = "12345"
        row[idx["stay_id"]] = "99999"
        row[idx["gender"]] = gender
        row[idx["age"]] = age
        row[idx["acuity"]] = str(acuity)
        row[idx["chiefcomplaint"]] = "Chest pain"
        row[idx["heartrate"]] = "80"
        row[idx["resprate"]] = "18"
        row[idx["o2sat"]] = "97"
        row[idx["sbp"]] = "120"
        row[idx["dbp"]] = "80"
        row[idx["temperature"]] = "98.6"
        row[idx["pain"]] = "5"
        row[idx["tiragecase"]] = "55-year-old male with chest pain"
        row[idx["Expert 1 Opinion"]] = "AGREE"
        row[idx["Expert 2 Opinion"]] = "AGREE"
        row[idx["Expert 3 Opinion"]] = ""
        row[idx["Final Decision"]] = decision
        # Fill intervention flags with 0
        for h in self.HEADERS:
            i = idx[h]
            if row[i] == "" and h not in (
                "hadm_id", "intime", "outtime", "race",
                "arrival_transport", "disposition",
                "Expert 3 Opinion",
            ):
                row[i] = "0"
        return row

    def _write_validate_csv(self, tmpdir, rows):
        path = os.path.join(tmpdir, "MIETIC-validate-samples.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.HEADERS)
            for row in rows:
                writer.writerow(row)
        return tmpdir

    def test_loads_retain_only(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_validate_csv(td, [
                self._make_row(acuity=1, decision="RETAIN"),
                self._make_row(acuity=2, decision="REMOVE"),
                self._make_row(acuity=3, decision="RETAIN"),
            ])
            cases = load_mietic_validated(td, retain_only=True)
            assert len(cases) == 2
            assert all(c.final_decision == "RETAIN" for c in cases)

    def test_loads_all_cases(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_validate_csv(td, [
                self._make_row(acuity=1, decision="RETAIN"),
                self._make_row(acuity=2, decision="REMOVE"),
            ])
            cases = load_mietic_validated(td, retain_only=False)
            assert len(cases) == 2

    def test_skips_invalid_acuity(self):
        with tempfile.TemporaryDirectory() as td:
            row = self._make_row(acuity=1, decision="RETAIN")
            idx = {h: i for i, h in enumerate(self.HEADERS)}
            row[idx["acuity"]] = ""  # invalid
            self._write_validate_csv(td, [
                row,
                self._make_row(acuity=3, decision="RETAIN"),
            ])
            cases = load_mietic_validated(td, retain_only=True)
            assert len(cases) == 1
            assert cases[0].acuity == 3

    def test_handles_missing_vitals(self):
        with tempfile.TemporaryDirectory() as td:
            row = self._make_row(acuity=1, decision="RETAIN")
            idx = {h: i for i, h in enumerate(self.HEADERS)}
            row[idx["heartrate"]] = ""
            row[idx["resprate"]] = ""
            row[idx["temperature"]] = ""
            self._write_validate_csv(td, [row])
            cases = load_mietic_validated(td, retain_only=True)
            assert len(cases) == 1
            assert cases[0].heartrate is None
            assert cases[0].resprate is None
            assert cases[0].temperature is None

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError):
                load_mietic_validated(td)

    def test_missing_columns_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "MIETIC-validate-samples.csv")
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["col1", "col2"])
                writer.writerow(["a", "b"])
            with pytest.raises(MIETICSchemaError, match="missing columns"):
                load_mietic_validated(td)

    def test_validated_summary(self):
        with tempfile.TemporaryDirectory() as td:
            self._write_validate_csv(td, [
                self._make_row(acuity=1, decision="RETAIN"),
                self._make_row(acuity=2, decision="RETAIN"),
                self._make_row(acuity=2, decision="RETAIN"),
            ])
            cases = load_mietic_validated(td, retain_only=True)
            s = validated_summary(cases)
            assert s["total"] == 3
            assert s["acuity_distribution"] == {1: 1, 2: 2}

    def test_handles_bom_in_first_column(self):
        """Simulate the actual MIETIC BOM corruption."""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "MIETIC-validate-samples.csv")
            # Write with BOM-corrupted first column name
            headers = list(self.HEADERS)
            headers[0] = "\u9518\u7e2e" + headers[0]  # 锘縮ubject_id
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow(self._make_row(acuity=2, decision="RETAIN"))
            cases = load_mietic_validated(td, retain_only=True)
            assert len(cases) == 1
            assert cases[0].acuity == 2


# ---------------------------------------------------------------------------
# Integration: load real MIETIC files if available
# ---------------------------------------------------------------------------

MIETIC_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "mimic-iv-ext-triage-instruction-corpus-1.0.0",
)


@pytest.mark.skipif(
    not os.path.isdir(MIETIC_DIR),
    reason="MIETIC dataset not present locally",
)
class TestRealMIETICData:
    """Smoke tests against the actual MIETIC files on disk."""

    def test_corpus_loads(self):
        entries = load_mietic_corpus(MIETIC_DIR, limit=100)
        assert len(entries) == 100
        assert all(e.esi_band in ("1", "2", "3-5") for e in entries)
        assert all(len(e.input_text) > 10 for e in entries)

    def test_validated_loads_retain(self):
        cases = load_mietic_validated(MIETIC_DIR, retain_only=True)
        assert len(cases) >= 30  # expect ~36 RETAIN
        assert all(1 <= c.acuity <= 5 for c in cases)
        assert all(c.final_decision == "RETAIN" for c in cases)

    def test_validated_all(self):
        cases = load_mietic_validated(MIETIC_DIR, retain_only=False)
        assert len(cases) == 50  # all valid cases

    def test_corpus_counts_match_expected(self):
        entries = load_mietic_corpus(MIETIC_DIR)
        s = corpus_summary(entries)
        # Expected: ~3001 ESI-1, ~3001 ESI-2, ~3627 ESI 3-5
        assert s["esi_1"] > 2900
        assert s["esi_2"] > 2900
        assert s["esi_3_5"] > 3500
        assert s["total"] > 9500
