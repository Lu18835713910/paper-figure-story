"""Regressions for U1: arrowheads visible without changing z-order."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_pptx as bp
import project_research_logic as pr
import render_logic as rr

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def node(nid, x, y):
    return {"id": nid, "title": "节点" + nid, "detail": "合成夹具",
            "role": "analysis", "x": x, "y": y}


def slide(edges, nodes):
    return {"meta": {"short_citation": "synthetic"}, "slides": [{
        "kind": "logic", "title": "U1 夹具", "lead": "夹具", "transition": "夹具",
        "diagram_type": "branch_merge", "nodes": nodes, "edges": edges}]}


def build(tmp, edges, nodes):
    from pptx import Presentation
    d = Path(tmp)
    j = d / "s.json"
    j.write_text(json.dumps(slide(edges, nodes), ensure_ascii=False), encoding="utf-8")
    t = d / "t.pptx"
    o = d / "o.pptx"
    bp.make_default_template(t)
    bp.build(j, o, t, "auto", False, False)
    return Presentation(str(o)).slides[0]


def tails(sl):
    out = []
    for s in sl.shapes:
        if not hasattr(s, "_element"):
            continue
        t = s._element.find(".//" + A + "tailEnd")
        if t is not None and t.get("type", "none") != "none":
            out.append((s, t))
    return out


class U1(unittest.TestCase):
    def test_builder_arrow_head_is_large(self):
        self.assertEqual(bp.ARROW_HEAD_SIZE, "lg")
        with tempfile.TemporaryDirectory() as tmp:
            sl = build(tmp, [{"from": "A", "to": "B", "relation": "motivates",
                              "provenance": "paper"}],
                       [node("A", 0.0, 0.5), node("B", 1.0, 0.5)])
            t = tails(sl)
            self.assertEqual(len(t), 1)
            self.assertEqual(t[0][1].get("w"), "lg")

    def test_builder_endpoint_retreat_is_bounded(self):
        self.assertTrue(0 < bp.ARROW_ENDPOINT_RETREAT_IN < 0.2)

    def test_rl_endpoint_retreat_bounded_and_direction_preserving(self):
        pts = [[0, 0], [100, 0], [100, 80], [400, 80]]
        out = pr.retreat_arrow_endpoint(pts)
        self.assertEqual(len(out), len(pts))
        self.assertEqual(out[:-1], pts[:-1])
        self.assertAlmostEqual(out[-1][0], 400 - pr.ARROW_ENDPOINT_RETREAT, places=6)
        self.assertAlmostEqual(out[-1][1], 80, places=6)
        # never reverses past the preceding corner
        tiny = [[0, 0], [2, 0]]
        self.assertEqual(pr.retreat_arrow_endpoint(tiny), tiny)
        self.assertEqual(pr.retreat_arrow_endpoint([[0, 0]]), [[0, 0]])

    def test_z_order_unchanged(self):
        """No wholesale z-order swap: connectors stay beneath node frames."""
        with tempfile.TemporaryDirectory() as tmp:
            sl = build(tmp, [{"from": "A", "to": "B", "relation": "motivates",
                              "provenance": "paper"}],
                       [node("A", 0.0, 0.5), node("B", 1.0, 0.5)])
            shapes = list(sl.shapes)
            conn = min(i for i, s in enumerate(shapes) if s.name.startswith("PFS_GRAPH_EDGE"))
            frame = min(i for i, s in enumerate(shapes) if s.name.startswith("PFS_GRAPH_NODE_")
                        and not s.name.startswith(("PFS_GRAPH_NODE_TITLE",
                                                   "PFS_GRAPH_NODE_DETAIL",
                                                   "PFS_GRAPH_NODE_FIGREF",
                                                   "PFS_GRAPH_NODE_BAR_")))
            self.assertLess(conn, frame)

    def test_undirected_relations_still_have_no_arrow(self):
        for rel in bp.UNDIRECTED_RELATIONS:
            with self.subTest(relation=rel):
                with tempfile.TemporaryDirectory() as tmp:
                    sl = build(tmp, [{"from": "A", "to": "B", "relation": rel,
                                      "provenance": "paper"}],
                               [node("A", 0.0, 0.5), node("B", 1.0, 0.5)])
                    self.assertEqual(len(tails(sl)), 0)
        for typ in ("parallel", "comparison", "shared_workflow"):
            self.assertFalse(pr.directed_relation({"type": typ, "identity": "AUTHOR_ARGUMENT"}))

    def test_same_column_route_avoids_intermediate_card(self):
        """N1(top) -> N3(bottom) in one column must not cross N2(middle)."""
        nodes = [node("N1", 0.5, 0.0), node("N2", 0.5, 0.5), node("N3", 0.5, 1.0)]
        with tempfile.TemporaryDirectory() as tmp:
            sl = build(tmp, [{"from": "N1", "to": "N3", "relation": "motivates",
                              "provenance": "paper"}], nodes)
            frames = []
            for s in sl.shapes:
                if s.name.startswith("PFS_GRAPH_NODE_") and not s.name.startswith(
                        ("PFS_GRAPH_NODE_TITLE", "PFS_GRAPH_NODE_DETAIL",
                         "PFS_GRAPH_NODE_FIGREF", "PFS_GRAPH_NODE_BAR_")):
                    frames.append((s.name, s.left, s.top, s.left + s.width, s.top + s.height))
            self.assertGreaterEqual(len(frames), 3)
            # the middle card must not be crossed by any vertical connector
            mid = next(f for f in frames if f[0].endswith("N2"))
            for s in sl.shapes:
                if not s.name.startswith("PFS_GRAPH_EDGE"):
                    continue
                x1, y1, x2, y2 = s.begin_x, s.begin_y, s.end_x, s.end_y
                if abs(x1 - x2) < 1000:  # vertical segment
                    crosses = (mid[1] + 5000 < x1 < mid[3] - 5000 and
                               min(y1, y2) < mid[4] and max(y1, y2) > mid[2])
                    self.assertFalse(crosses, "vertical leg crosses intermediate card")

    def test_render_logic_scene_contract_after_retreat(self):
        """draw_scene + validate_scene must agree on retreated endpoints."""
        from pptx import Presentation
        from pptx.util import Inches

        def n(i):
            return {"id": i, "kind": "finding", "identity": "SCIENTIFIC_EVIDENCE",
                    "title": i, "short_text": i, "detail_text": i,
                    "source_ids": ["S"], "statement_ids": [], "source_entity_ids": [],
                    "field_bindings": []}
        model = {"nodes": [n("A"), n("B")],
                 "edges": [{"id": "E", "from": "A", "to": "B", "type": "progression",
                            "identity": "SCIENTIFIC_EVIDENCE"}],
                 "core": {"nodes": ["A", "B"], "edges": ["E"]}, "branches": [],
                 "layout": {"B": {"width": 1400, "height": 700,
                                  "positions": {"A": [60, 150, 460, 260],
                                                "B": [820, 150, 460, 260]},
                                  "routes": {}}},
                 "sources": {"S": {"physical_page": 1}}, "snapshot": "u1",
                 "paper_title": "synthetic"}
        net = {"paper": {"paper_type": "original_research"}}
        product = pr.build_scene(net, model, "B")
        scene = product["slides"][0]
        prs = Presentation()
        prs.slide_width = Inches(product["width"] / 96)
        prs.slide_height = Inches(product["height"] / 96)
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        rr.draw_scene(sl, product, scene)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.pptx"
            prs.save(str(p))
            reopened = Presentation(str(p)).slides[0]
            rr.validate_scene(reopened, scene)  # raises on endpoint drift
            t = tails(reopened)
            self.assertEqual(len(t), 1)
            self.assertEqual(t[0][1].get("w"), "lg")


if __name__ == "__main__":
    unittest.main()
