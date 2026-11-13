"""PFS→RLD 论证单元派生：只用登记语句、不用标签、保留 PDF 身份、三态分明。"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rld_units as ru  # noqa: E402

DOC_SHA = "a" * 64


def network(with_claim=True, doc_sha=DOC_SHA):
    stmts = [
        {"id": "S_Q", "role": "purpose", "text": "does X change Y", "source_refs": [
            {"document_id": "D", "locator": {"physical_page": 1, "section": "intro"},
             "verification": "direct_checked"}]},
        {"id": "S_D", "role": "design", "text": "X versus vehicle", "source_refs": [
            {"document_id": "D", "locator": {"physical_page": 2, "section": "methods"},
             "verification": "direct_checked"}]},
        {"id": "S_O", "role": "result", "text": "Y increased", "source_refs": [
            {"document_id": "D", "locator": {"physical_page": 3, "section": "results"},
             "verification": "direct_checked"}]},
        {"id": "S_L", "role": "limitation", "text": "single model only", "source_refs": [
            {"document_id": "D", "locator": {"physical_page": 3, "section": "limits"},
             "verification": "direct_checked"}]},
    ]
    if with_claim:
        stmts.append({"id": "S_C", "role": "interpretation", "text": "X promotes Y",
                      "source_refs": [{"document_id": "D",
                                       "locator": {"physical_page": 4, "section": "discussion"},
                                       "verification": "direct_checked"}]})
    return {
        "version": "pfs-evidence-network-1", "snapshot": "net-snap",
        "paper": {"id": "P", "paper_type": "original_research", "title": "t",
                  "documents": [{"id": "D", "role": "main_paper", "format": "pdf", "title": "t",
                                 "version": "v", "availability": "available",
                                 "sha256": doc_sha, "hash_status": "verified",
                                 "source_locator": "whole file", "physical_page_count": 9}]},
        "nodes": [], "edges": [], "statements": stmts,
    }


def logic(with_claim=True):
    cids = ["S_C", "S_L"] if with_claim else ["S_L"]
    return {
        "version": "pfs-research-logic-1", "snapshot": "logic-snap",
        "nodes": [
            {"id": "LN_Q", "identity": "AUTHOR_ARGUMENT", "label": "PROMOTES labels must not be used",
             "statement_ids": ["S_Q", "S_D"], "source_entity_ids": []},
            {"id": "LN_C", "identity": "AUTHOR_INTERPRETATION", "label": "X PROMOTES Y (label)",
             "statement_ids": cids, "source_entity_ids": []},
        ],
        "edges": [{"id": "LE1", "from": "LN_Q", "to": "LN_C", "type": "evidence_convergence",
                   "identity": "SCIENTIFIC_EVIDENCE", "rationale": "measurement supports claim",
                   "alternatives": ["association only"]}],
    }


def index(doc_sha=DOC_SHA):
    return {"version": "pfs-scientific-index-1", "file_sha256": doc_sha,
            "reading_status": "AVAILABLE_CONTENT_READ", "sources": {}, "facets": {}}


class Derivation(unittest.TestCase):
    def test_one_unit_per_logic_node(self):
        d = ru.build(index(), network(), logic())
        self.assertEqual(2, d["counts"]["units"])
        self.assertEqual({"AU_LN_Q", "AU_LN_C"}, {u["unit_id"] for u in d["units"]})

    def test_claim_comes_from_registered_statement(self):
        d = ru.build(index(), network(), logic())
        u = {x["unit_id"]: x for x in d["units"]}["AU_LN_C"]
        self.assertEqual("X promotes Y", u["claim"]["value"])
        self.assertEqual(ru.EXPLICIT, u["claim"]["status"])
        self.assertEqual(["S_C"], u["claim"]["source_statement_ids"])

    def test_label_is_never_used_as_claim(self):
        """逻辑节点标签写着 PROMOTES，但没有 interpretation 语句时必须判信息不足。"""
        d = ru.build(index(), network(with_claim=False), logic(with_claim=False))
        u = {x["unit_id"]: x for x in d["units"]}["AU_LN_C"]
        self.assertIsNone(u["claim"]["value"])
        self.assertEqual(ru.MISSING, u["claim"]["status"])
        self.assertFalse(u["usable_for_causal_check"])
        self.assertNotIn("PROMOTES", json.dumps(u, ensure_ascii=False))

    def test_missing_fields_are_marked_not_invented(self):
        d = ru.build(index(), network(with_claim=False), logic(with_claim=False))
        u = {x["unit_id"]: x for x in d["units"]}["AU_LN_C"]
        for k in ("question", "design", "observations", "claim"):
            self.assertEqual(ru.MISSING, u[k]["status"], k)
        self.assertEqual(2, d["counts"]["units_without_claim_statement"])
        self.assertEqual(0, d["counts"]["units_with_claim"])

    def test_pdf_identity_preserved(self):
        d = ru.build(index(), network(), logic())
        self.assertEqual(DOC_SHA, d["identity"]["index_file_sha256"])
        refs = d["units"][0]["source_refs"]
        self.assertTrue(refs)
        self.assertTrue(all(r["document_sha256"] == DOC_SHA for r in refs))
        self.assertTrue(all(r["document_id"] == "D" for r in refs))

    def test_pdf_identity_mismatch_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            ru.build(index(), network(doc_sha="b" * 64), logic())
        self.assertIn("PDF_IDENTITY_MISMATCH", str(cm.exception))

    def test_premises_are_agent_reconstructed(self):
        d = ru.build(index(), network(), logic())
        u = {x["unit_id"]: x for x in d["units"]}["AU_LN_C"]
        self.assertEqual(ru.AGENT, u["premises"]["status"])
        self.assertEqual("LE1", u["premises"]["value"][0]["edge_id"])

    def test_comparison_conditions_stay_insufficient(self):
        d = ru.build(index(), network(), logic())
        for u in d["units"]:
            self.assertEqual(ru.MISSING, u["comparison_conditions"]["status"])

    def test_identity_block_records_snapshots(self):
        d = ru.build(index(), network(), logic())
        self.assertEqual("net-snap", d["identity"]["network_snapshot"])
        self.assertEqual("logic-snap", d["identity"]["logic_snapshot"])


if __name__ == "__main__":
    unittest.main()
