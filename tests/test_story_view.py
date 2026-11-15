"""Regressions for the story-A display layer (display only; model untouched)."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import story_view as sv


def fixture():
    nodes = [{"id": n, "kind": "task", "identity": "SCIENTIFIC_EVIDENCE",
              "title": n, "short_text": n, "source_ids": ["S"],
              "statement_ids": [], "source_entity_ids": [], "field_bindings": []}
             for n in ("A", "B", "C", "D")]
    edges = [
        {"id": "E1", "from": "A", "to": "B", "type": "question_fork",
         "identity": "AUTHOR_ARGUMENT", "source_ids": ["S"]},
        {"id": "E2", "from": "B", "to": "C", "type": "shared_workflow",
         "identity": "SHARED_PROTOCOL", "source_ids": ["S"]},
        {"id": "E3", "from": "C", "to": "D", "type": "evidence_convergence",
         "identity": "SCIENTIFIC_EVIDENCE", "source_ids": ["S"]},
    ]
    model = {"nodes": nodes, "edges": edges, "snapshot": "story-fixture",
             "sources": {"S": {"physical_page": 1}}}
    units = [
        {"id": "U1", "label": "WHY", "title": "为什么做",
         "body": "背景与问题", "node_ids": ["A"], "rect": [20, 20, 300, 200]},
        {"id": "U2", "label": "BASE", "title": "基础",
         "body": "共享实验", "node_ids": ["B"], "rect": [340, 20, 300, 200]},
        {"id": "U3", "label": "STRATEGY", "title": "策略",
         "body": "并列策略", "node_ids": ["C"], "rect": [20, 240, 300, 200]},
        {"id": "U4", "label": "FINDING", "title": "发现",
         "body": "关键发现", "node_ids": ["D"], "rect": [340, 240, 300, 200]},
    ]
    links = [
        {"id": "L1", "from": "U1", "to": "U2", "relation_ids": ["E1"], "arrow": True},
        {"id": "L2", "from": "U2", "to": "U3", "relation_ids": ["E2"], "arrow": False},
        {"id": "L3", "from": "U3", "to": "U4", "relation_ids": ["E3"], "arrow": True},
    ]
    story = {"id": "story-fixture", "review": {"reviewed_by": "test"},
             "canvas": {"width": 1280, "height": 622},
             "title": "fixture", "citation": "fixture", "units": units, "links": links}
    return model, story


class StoryLayer(unittest.TestCase):
    def test_valid_fixture_passes(self):
        m, s = fixture()
        r = sv.validate_story(m, s)
        self.assertTrue(r["valid"], r["errors"])
        self.assertEqual(r["covered_nodes"], 4)

    def test_missing_node_is_rejected(self):
        m, s = fixture()
        s["units"][3]["node_ids"] = []
        r = sv.validate_story(m, s)
        self.assertIn("NODES_NOT_DISPLAYED:D", r["errors"])

    def test_causal_arrow_on_undirected_relation_is_rejected(self):
        m, s = fixture()
        s["links"][1]["arrow"] = True
        r = sv.validate_story(m, s)
        self.assertTrue(any(e.startswith("CAUSAL_ARROW_ON_UNDIRECTED") for e in r["errors"]))

    def test_relation_unit_mismatch_is_rejected(self):
        m, s = fixture()
        s["links"][0]["to"] = "U3"
        r = sv.validate_story(m, s)
        self.assertTrue(any(e.startswith("RELATION_UNIT_MISMATCH") for e in r["errors"]))

    def test_mixed_directed_and_undirected_link_is_rejected(self):
        m, s = fixture()
        s["links"][1]["relation_ids"] = ["E2", "E3"]
        s["links"][1]["arrow"] = True
        r = sv.validate_story(m, s)
        self.assertTrue(any(e.startswith("MIXED_RELATION_SEMANTICS") for e in r["errors"]), r["errors"])
        self.assertTrue(any(e.startswith("CAUSAL_ARROW_ON_UNDIRECTED") for e in r["errors"]), r["errors"])

    def test_arrow_on_mixed_link_is_rejected_even_if_only_one_undirected(self):
        m, s = fixture()
        s["links"][2]["relation_ids"] = ["E3", "E2"]
        s["links"][2]["arrow"] = True
        r = sv.validate_story(m, s)
        self.assertTrue(any(e.startswith("MIXED_RELATION_SEMANTICS") for e in r["errors"]), r["errors"])

    def test_missing_reviewer_is_rejected(self):
        m, s = fixture()
        s.pop("review")
        r = sv.validate_story(m, s)
        self.assertIn("STORY_REVIEW_REQUIRED", r["errors"])

    def test_link_without_provenance_is_rejected(self):
        m, s = fixture()
        s["links"].append({"id": "L9", "from": "U3", "to": "U4", "relation_ids": []})
        r = sv.validate_story(m, s)
        self.assertIn("LINK_WITHOUT_PROVENANCE", r["errors"])

    def test_scene_is_deterministic_and_native(self):
        m, s = fixture()
        a, _, info = sv.build_scene(m, s)
        b, _, _ = sv.build_scene(m, s)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(info["scale"], round(min(12.633 / (1280 / 96), 6.15 / (622 / 96)), 4))
        self.assertTrue(all(e["kind"] in ("rect", "text") for e in a["slides"][0]["elements"]))

    def test_body_size_meets_sixteen_pt_on_main(self):
        m, s = fixture()
        for u in s["units"]:
            u["body_px"] = 23
        _, _, info = sv.build_scene(m, s)
        self.assertGreaterEqual(info["body_pt_on_main"], 16.0)

    def test_model_is_never_mutated(self):
        m, s = fixture()
        before = copy.deepcopy(m)
        sv.build_scene(m, s)
        self.assertEqual(m, before)


if __name__ == "__main__":
    unittest.main()
