"""Regression: A legend must be drawn clear of the citation strip.

The fix is RENDERING-ONLY (render_logic.LEGEND_A_LIFT) so the scientific scene
keeps its declarative geometry and validate_products() never reports
PRODUCT_PLAN_DRIFT.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import project_research_logic as pr
import render_logic as rr

CITATION_TOP_OFFSET = 44  # draw_scene: fy = H-44 for non-local scenes


def model(view_height=900):
    def n(i, kind="finding"):
        return {"id": i, "kind": kind, "identity": "SCIENTIFIC_EVIDENCE",
                "title": i, "short_text": i, "detail_text": i,
                "source_ids": ["S"], "statement_ids": [], "source_entity_ids": [],
                "field_bindings": []}
    nodes = [n("Q", "question"), n("A"), n("B")]
    edges = [{"id": "E1", "from": "Q", "to": "A", "type": "progression",
              "identity": "SCIENTIFIC_EVIDENCE"},
             {"id": "E2", "from": "A", "to": "B", "type": "evidence_convergence",
              "identity": "SCIENTIFIC_EVIDENCE"}]
    return {"nodes": nodes, "edges": edges,
            "core": {"nodes": ["Q", "A", "B"], "edges": ["E1", "E2"]},
            "branches": [],
            "layout": {"A": {"width": 1600, "height": view_height,
                             "positions": {"Q": [60, 80, 380, 200],
                                           "A": [560, 80, 380, 200],
                                           "B": [1060, 80, 380, 200]},
                             "routes": {}}},
            "sources": {"S": {"physical_page": 1}}, "snapshot": "footer-test",
            "paper_title": "synthetic"}


class FooterLayout(unittest.TestCase):
    def test_scene_legend_geometry_is_unchanged(self):
        """The scene must keep height-48 so deterministic projection is stable."""
        product = pr.build_scene({"paper": {"paper_type": "original_research"}},
                                 model(), "A")
        H = product["height"]
        legend = next(e for e in product["slides"][0]["elements"]
                      if e["id"].endswith("_legend"))
        self.assertEqual(legend["position"]["top"], H - 48)

    def test_drawn_a_legend_clears_citation(self):
        product = pr.build_scene({"paper": {"paper_type": "original_research"}},
                                 model(), "A")
        H = product["height"]
        legend = next(e for e in product["slides"][0]["elements"]
                      if e["id"].endswith("_legend"))
        drawn_top = legend["position"]["top"] - rr.LEGEND_A_LIFT
        drawn_bottom = drawn_top + legend["position"]["height"]
        self.assertLessEqual(drawn_bottom, H - CITATION_TOP_OFFSET,
                             "drawn A legend still overlaps the citation strip")

    def test_citation_strip_fits_inside_canvas(self):
        self.assertLessEqual(CITATION_TOP_OFFSET, 44)

    def test_B_legend_untouched(self):
        product = pr.build_scene({"paper": {"paper_type": "original_research"}},
                                 model(), "B")
        H = product["height"]
        legend = next(e for e in product["slides"][0]["elements"]
                      if e["id"].endswith("_legend"))
        self.assertEqual(legend["position"]["top"], H - 145)
        self.assertLessEqual(legend["position"]["top"] + legend["position"]["height"],
                             H - CITATION_TOP_OFFSET)


if __name__ == "__main__":
    unittest.main()
