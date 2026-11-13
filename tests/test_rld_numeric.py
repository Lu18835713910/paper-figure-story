"""数值门禁六态 + 主张级均值比较（含边界与负例）。"""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rld_numeric as num  # noqa: E402

AXIS = ["T1", "T2", "T3"]


def registry(rows, pdf_sha="0" * 64):
    return {"schema": "demo", "source_pdf_sha256": pdf_sha,
            "cells": [{"metric": m, "treatment": g, "stage": s, "value": v}
                      for (m, g, s), v in rows.items()]}


class Files:
    """在临时目录里造 registry + manifest，并返回独立锚点。"""

    def __init__(self, reg):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.reg = d / "registry.json"
        self.reg.write_text(json.dumps(reg), encoding="utf-8")
        self.manifest = d / "manifest.json"
        self.manifest.write_text(json.dumps({
            "canonical_registry_sha256": self._sha(self.reg)}), encoding="utf-8")
        self.anchor = self._sha(self.manifest)

    @staticmethod
    def _sha(p):
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

    def close(self):
        self.dir.cleanup()


class Gate(unittest.TestCase):
    U_NUM = {"unit_id": "U", "kind": "NUMERIC_COMPARISON"}
    U_TXT = {"unit_id": "U", "kind": "SCIENTIFIC_INTERPRETATION"}

    def test_non_numeric(self):
        self.assertEqual("NOT_APPLICABLE", num.gate(self.U_TXT, None, None)["status"])

    def test_missing_registry(self):
        self.assertEqual("EVIDENCE_REQUIRED", num.gate(self.U_NUM, None, None)["status"])

    def test_anchor_required(self):
        f = Files(registry({}))
        try:
            r = num.gate(self.U_NUM, f.reg, f.manifest, None)
            self.assertEqual("ANCHOR_REQUIRED", r["status"])
        finally:
            f.close()

    def test_manifest_anchor_mismatch_blocks(self):
        f = Files(registry({}))
        try:
            r = num.gate(self.U_NUM, f.reg, f.manifest, "f" * 64)
            self.assertEqual("STOP_MANIFEST_NOT_ANCHORED", r["status"])
        finally:
            f.close()

    def test_legal(self):
        f = Files(registry({}))
        try:
            r = num.gate(self.U_NUM, f.reg, f.manifest, f.anchor)
            self.assertEqual("AVAILABLE", r["status"])
        finally:
            f.close()

    def test_tampered_registry_blocks(self):
        f = Files(registry({("M", "G", "T1"): 1.0}))
        try:
            reg = json.loads(f.reg.read_text(encoding="utf-8"))
            reg["cells"][0]["value"] = 9.9
            f.reg.write_text(json.dumps(reg), encoding="utf-8")
            r = num.gate(self.U_NUM, f.reg, f.manifest, f.anchor)
            self.assertEqual("STOP_REGISTRY_NOT_CANONICAL", r["status"])
        finally:
            f.close()

    def test_manifest_without_pin_blocks(self):
        f = Files(registry({}))
        try:
            f.manifest.write_text(json.dumps({"note": "no pin"}), encoding="utf-8")
            r = num.gate(self.U_NUM, f.reg, f.manifest, f._sha(f.manifest))
            self.assertEqual("STOP_REGISTRY_NOT_CANONICAL", r["status"])
        finally:
            f.close()


class Evaluate(unittest.TestCase):
    def ev(self, rows, claims, axis=AXIS):
        doc = {"schema": "rld_numeric_claims_v1",
               "axis": {"order": axis},
               "cells_key": {"metric": "metric", "group": "treatment",
                             "series": "stage", "value": "value"},
               "claims": claims}
        return num.evaluate(doc, registry(rows))

    def test_ordered_increase_supports(self):
        rows = {("M", "G", t): v for t, v in zip(AXIS, [1.0, 2.0, 3.0])}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "ordered_by_series", "direction": "increase"}])
        self.assertEqual("SUPPORTS", r["results"][0]["verdict"])
        self.assertEqual({"SUPPORTS": 1, "REFUTES": 0, "INSUFFICIENT": 0}, r["summary"])

    def test_ordered_decrease_refutes(self):
        rows = {("M", "G", t): v for t, v in zip(AXIS, [1.0, 2.0, 3.0])}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "ordered_by_series", "direction": "decrease"}])
        self.assertEqual("REFUTES", r["results"][0]["verdict"])

    def test_extremum_at_last(self):
        rows = {("M", "G", t): v for t, v in zip(AXIS, [5.0, 3.0, 1.0])}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "extremum_at_last", "extremum": "min"}])
        self.assertEqual("SUPPORTS", r["results"][0]["verdict"])
        rows2 = {("M", "G", t): v for t, v in zip(AXIS, [1.0, 5.0, 3.0])}
        r2 = self.ev(rows2, [{"claim_id": "c1", "metric": "M", "group": "G",
                              "predicate": "extremum_at_last", "extremum": "min"}])
        self.assertEqual("REFUTES", r2["results"][0]["verdict"])

    def test_below_comparator_all_series(self):
        rows = {("M", "G", t): v for t, v in zip(AXIS, [1.0, 1.0, 1.0])}
        rows.update({("M", "CK", t): v for t, v in zip(AXIS, [2.0, 2.0, 2.0])})
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "comparator_group": "CK",
                            "predicate": "below_comparator_all_series"}])
        self.assertEqual("SUPPORTS", r["results"][0]["verdict"])
        self.assertIn(" < ", r["results"][0]["rule"])
        rows[("M", "CK", "T2")] = 0.5      # 中间一期反转 → 必须 REFUTES
        r2 = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                             "comparator_group": "CK",
                             "predicate": "below_comparator_all_series"}])
        self.assertEqual("REFUTES", r2["results"][0]["verdict"])

    def test_missing_cells_give_insufficient_not_guess(self):
        rows = {("M", "G", "T1"): 1.0, ("M", "G", "T2"): 2.0}   # 缺 T3
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "ordered_by_series", "direction": "increase"}])
        self.assertEqual("INSUFFICIENT", r["results"][0]["verdict"])
        self.assertTrue(r["results"][0]["missing_cells"])

    def test_missing_comparator_group_is_insufficient(self):
        rows = {("M", "G", t): 1.0 for t in AXIS}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "below_comparator_all_series"}])
        self.assertEqual("INSUFFICIENT", r["results"][0]["verdict"])

    def test_unknown_predicate_is_insufficient(self):
        rows = {("M", "G", t): 1.0 for t in AXIS}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "statistically_significant"}])
        self.assertEqual("INSUFFICIENT", r["results"][0]["verdict"])

    def test_every_result_carries_source_cells_and_boundary(self):
        rows = {("M", "G", t): v for t, v in zip(AXIS, [1.0, 2.0, 3.0])}
        r = self.ev(rows, [{"claim_id": "c1", "metric": "M", "group": "G",
                            "predicate": "ordered_by_series", "direction": "increase",
                            "source": {"source_page": 7}}])
        x = r["results"][0]
        self.assertEqual(3, len(x["cells_used"]))
        self.assertIn("不构成统计显著性", x["boundary"])
        self.assertIn("不构成因果", x["boundary"])
        self.assertEqual(7, x["source"]["source_page"])

    def test_axis_can_come_from_data(self):
        rows = {("M", "G", t): v for t, v in zip(["A", "B"], [1.0, 2.0])}
        doc = {"schema": "rld_numeric_claims_v1",
               "cells_key": {"metric": "metric", "group": "treatment",
                             "series": "stage", "value": "value"},
               "claims": [{"claim_id": "c1", "metric": "M", "group": "G",
                           "predicate": "ordered_by_series", "direction": "increase"}]}
        r = num.evaluate(doc, registry(rows))
        self.assertEqual(["A", "B"], r["axis"])
        self.assertEqual("SUPPORTS", r["results"][0]["verdict"])


if __name__ == "__main__":
    unittest.main()
