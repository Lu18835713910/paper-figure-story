"""Regressions for the three v1.2.0 maintenance fixes (evidence-bound).

FIX-1  Builder argument graph: symmetric relations must not be serialized
       with a direction arrow, must not create topological ordering, and
       right-to-left geometry must not override declared provenance.
FIX-2  Research Logic safe_route: bottom fallback channels are bounded and
       reusable, so B canvases no longer inflate with the global edge index.
FIX-3  Projection display contract: missing kind/short_text/... is reported
       as LOGIC_DISPLAY_FIELD_REQUIRED at preflight instead of a bare KeyError.

All fixtures here are synthetic and self-contained. No private case data,
no frozen blind-test paths, no paper-specific coordinates.
"""
from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_pptx as bp
import project_research_logic as pr

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def make_node(nid, x, y):
    return {"id": nid, "title": "节点" + nid, "detail": "合成夹具",
            "role": "analysis", "x": x, "y": y}


def make_slide(edges, nodes=None):
    nodes = nodes or [make_node("A", 0.0, 0.5), make_node("B", 1.0, 0.5)]
    return {"meta": {"short_citation": "synthetic"}, "slides": [{
        "kind": "logic", "title": "合成关系夹具", "lead": "夹具",
        "transition": "夹具", "diagram_type": "branch_merge",
        "nodes": nodes, "edges": edges,
    }]}


def build_and_read_edges(manifest, tmp):
    from pptx import Presentation
    data = Path(tmp) / "slides.json"
    data.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    template = Path(tmp) / "template.pptx"
    out = Path(tmp) / "out.pptx"
    bp.make_default_template(template)
    bp.build(data, out, template, "auto", False, False)
    prs = Presentation(str(out))
    rows = []
    for s in prs.slides[0].shapes:
        if not s.name.startswith("PFS_GRAPH_EDGE"):
            continue
        tail = s._element.find(".//{%s}tailEnd" % A_NS)
        dash = s._element.find(".//{%s}prstDash" % A_NS)
        rows.append({"arrow": bool(tail is not None and tail.get("type", "none") != "none"),
                     "dashed": bool(dash is not None and dash.get("val") != "solid")})
    return rows


class Fix1BuilderRelationSemantics(unittest.TestCase):
    def test_undirected_relations_have_no_arrow(self):
        """Correct input: parallel / compares / alternative are symmetric."""
        for relation in sorted(bp.UNDIRECTED_RELATIONS):
            with self.subTest(relation=relation):
                with tempfile.TemporaryDirectory() as tmp:
                    edges = [{"from": "A", "to": "B", "relation": relation,
                              "provenance": "paper"}]
                    rows = build_and_read_edges(make_slide(edges), tmp)
                    self.assertTrue(rows, "no connectors were serialized")
                    self.assertFalse(any(r["arrow"] for r in rows),
                                     relation + " was serialized with a direction arrow")

    def test_directed_relations_keep_arrow(self):
        """Correct input: registered directional relations keep exactly one arrow."""
        for relation in ("motivates", "tests", "supports", "extends", "integrates"):
            with self.subTest(relation=relation):
                with tempfile.TemporaryDirectory() as tmp:
                    edges = [{"from": "A", "to": "B", "relation": relation,
                              "provenance": "paper"}]
                    rows = build_and_read_edges(make_slide(edges), tmp)
                    self.assertEqual(sum(1 for r in rows if r["arrow"]), 1, relation)

    def test_parallel_is_not_a_topological_dependency(self):
        """Symmetric edges must not push one endpoint into a later layer."""
        nodes = [{"id": "A", "title": "A", "detail": "x", "role": "analysis"},
                 {"id": "B", "title": "B", "detail": "x", "role": "analysis"}]
        edges = [{"from": "A", "to": "B", "relation": "parallel", "provenance": "paper"}]
        pos, cw, ch = bp._graph_layout(nodes, edges, 11.85, 4.52)
        self.assertEqual(pos["A"][0], pos["B"][0], "parallel edge created an ordering layer")
        directed = [{"from": "A", "to": "B", "relation": "motivates", "provenance": "paper"}]
        pos2, _, _ = bp._graph_layout(nodes, directed, 11.85, 4.52)
        self.assertLess(pos2["A"][0], pos2["B"][0], "directed edge lost its ordering")

    def test_right_to_left_geometry_does_not_override_provenance(self):
        """Fault injection: a paper-grounded reverse edge is not silently
        relabelled as presentation inference (dashed) just because of geometry."""
        nodes = [make_node("A", 1.0, 0.5), make_node("B", 0.0, 0.5)]
        with tempfile.TemporaryDirectory() as tmp:
            rows = build_and_read_edges(make_slide(
                [{"from": "A", "to": "B", "relation": "integrates",
                  "provenance": "paper"}], nodes), tmp)
            self.assertFalse(any(r["dashed"] for r in rows))
            self.assertEqual(sum(1 for r in rows if r["arrow"]), 1)
        with tempfile.TemporaryDirectory() as tmp:
            rows = build_and_read_edges(make_slide(
                [{"from": "A", "to": "B", "relation": "feedback",
                  "provenance": "paper"}], nodes), tmp)
            self.assertTrue(any(r["dashed"] for r in rows),
                            "explicit feedback must keep its dashed returning loop")

    def test_frozen_main_slide3_pattern_m3_m4_parallel(self):
        """Exact reproduction of the reported m3->m4 relation=parallel case."""
        nodes = [make_node("m3", 0.5, 0.18), make_node("m4", 0.5, 0.82)]
        edges = [{"from": "m3", "to": "m4", "relation": "parallel", "provenance": "paper"}]
        with tempfile.TemporaryDirectory() as tmp:
            rows = build_and_read_edges(make_slide(edges, nodes), tmp)
            self.assertTrue(rows)
            self.assertFalse(any(r["arrow"] for r in rows))

    def test_research_logic_projector_still_undirected(self):
        """Both drawers must agree on the symmetric types."""
        for typ in ("parallel", "comparison", "shared_workflow"):
            self.assertFalse(pr.directed_relation({"type": typ, "identity": "AUTHOR_ARGUMENT"}))
        self.assertTrue(pr.directed_relation({"type": "progression", "identity": "AUTHOR_ARGUMENT"}))


POS = {"A": [10, 210, 200, 200], "B": [310, 210, 200, 200], "C": [610, 210, 200, 200]}


class Fix2BoundedFallbackChannels(unittest.TestCase):
    def test_fallback_still_avoids_nodes(self):
        for lane in (0, 1, 2, 3, 23, 99):
            with self.subTest(lane=lane):
                points = pr.safe_route(POS, "A", "C", lane, 1200)
                self.assertFalse(pr.route_hits_node(points, POS, {"A", "C"}))

    def test_channel_is_bounded_for_large_lane(self):
        """Boundary: the global edge index must not push the detour down."""
        base = max(p[1] + p[3] for p in POS.values()) + 60
        bottoms = {max(y for _, y in pr.safe_route(POS, "A", "C", lane, 1200))
                   for lane in range(0, 40)}
        self.assertLessEqual(max(bottoms), base + 2 * 26 + 1)
        self.assertLessEqual(len(bottoms), 3, "more than the bounded channel set")

    def test_uncollided_route_is_unchanged(self):
        """No fallback triggered -> the original orthogonal route is returned."""
        direct = pr._route(POS["A"], POS["B"], 0, 1200)
        self.assertEqual(pr.safe_route(POS, "A", "B", 0, 1200), direct)

    def test_b_canvas_not_inflated_by_fallback(self):
        """B canvas growth stays bounded when many edges need fallback channels."""
        def node(nid, kind="finding"):
            return {"id": nid, "kind": kind, "identity": "SCIENTIFIC_EVIDENCE",
                    "title": nid, "short_text": nid, "detail_text": nid,
                    "source_ids": ["S"], "statement_ids": [], "source_entity_ids": [],
                    "field_bindings": []}
        ids = ["N%02d" % i for i in range(12)]
        positions = {nid: [80 + (i % 4) * 700, 150 + (i // 4) * 500, 600, 300]
                     for i, nid in enumerate(ids)}
        edges = [{"id": "E%02d" % i, "from": ids[0], "to": ids[(i % 11) + 1],
                  "type": "evidence_convergence", "identity": "SCIENTIFIC_EVIDENCE",
                  "display_label": "x"} for i in range(24)]
        model = {"nodes": [node(n, "question" if i == 0 else "finding")
                           for i, n in enumerate(ids)],
                 "edges": edges, "core": {"nodes": ids, "edges": [e["id"] for e in edges]},
                 "branches": [], "layout": {}, "sources": {"S": {"physical_page": 1}},
                 "snapshot": "syn", "paper_title": "synthetic"}
        net = {"paper": {"paper_type": "original_research"}}
        declared = pr._default_positions(model, "B", list(model["layout"].get("positions", {})) or
                                         [n["id"] for n in model["nodes"]])
        product = pr.build_scene(net, model, "B")
        self.assertLessEqual(product["height"] - declared["height"], 400,
                             "fallback channels still inflate the B canvas")


class Fix3DisplayContractPreflight(unittest.TestCase):
    FIELDS = pr.DISPLAY_NODE_FIELDS

    def base(self):
        n = {"id": "N1", "kind": "finding", "identity": "SCIENTIFIC_EVIDENCE",
             "title": "T", "short_text": "S", "source_ids": [], "statement_ids": [],
             "source_entity_ids": [], "field_bindings": []}
        return {"nodes": [n], "edges": []}

    def test_valid_model_passes(self):
        self.assertTrue(pr.validate_display_contract(self.base())["valid"])

    def test_missing_kind_reports_actionable_code(self):
        """Wrong input: the frozen KeyError: 'kind' must become a clear preflight error."""
        m = self.base(); del m["nodes"][0]["kind"]
        q = pr.validate_display_contract(m)
        self.assertFalse(q["valid"])
        self.assertIn("N1 / kind", q["errors"])
        with self.assertRaisesRegex(ValueError, "LOGIC_DISPLAY_FIELD_REQUIRED"):
            pr.require_display_contract(m)
        self.assertFalse(any("KeyError" in e for e in q["errors"]))

    def test_missing_multiple_fields_lists_all(self):
        m = self.base()
        for f in ("short_text", "field_bindings", "source_ids"):
            del m["nodes"][0][f]
        q = pr.validate_display_contract(m)
        self.assertEqual(len(q["errors"]), 3)
        self.assertTrue(all("/ " in e for e in q["errors"]))

    def test_empty_and_unknown_node_boundaries(self):
        self.assertTrue(pr.validate_display_contract({"nodes": []})["valid"])
        q = pr.validate_display_contract(self.base(), ["GHOST"])
        self.assertFalse(q["valid"])
        self.assertIn("NODE_NOT_FOUND", q["errors"][0])

    def test_build_scene_preflight_precedes_traceback(self):
        """End-to-end: a scientifically valid-looking but display-incomplete
        model fails with a named code rather than an untyped KeyError."""
        m = self.base(); del m["nodes"][0]["kind"]
        m.update(core={"nodes": ["N1"], "edges": []}, branches=[], layout={},
                 sources={}, snapshot="s", paper_title="s")
        with self.assertRaisesRegex(ValueError, "LOGIC_DISPLAY_FIELD_REQUIRED"):
            pr.build_scene({"paper": {"paper_type": "original_research"}}, m, "B")

    def test_scientific_validator_semantics_unchanged(self):
        """The fix must not weaken research_logic.validate_model's own gates."""
        import research_logic as rl
        q = rl.validate_model({"version": rl.VERSION, "snapshot": "x"},
                              verify_files=False)
        self.assertFalse(q["valid"])
        self.assertIn("REVIEW_UPGRADE", [e["code"] for e in q["errors"]])
        self.assertIn("LOGIC_INPUT", [e["code"] for e in q["errors"]])


if __name__ == "__main__":
    unittest.main()
