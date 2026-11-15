"""Regression: a dense question page must keep its bullets inside the card.

Six long bullets at the old heuristic size (19pt) overflowed DECOR_card and
printed over the citation strip in both PowerPoint and LibreOffice.
"""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_pptx as bp

EMU = 914400
SIX = [
    "【补件原文】S15 Appendix 用 Re/We 数估算：250 ml/min 下惯性超过毛细力的区域 <0.2 mm，"
    "小于砂粒 d50=0.713 mm，故惯性力不决定观测驱替形态。",
    "【Agent 建模判断】该支线在正文未被引用，作为独立不连通分量保留，不强行接入主比较网络。",
    "【原文限制】仅一种均质砂；实验数据复用自文献 [4]；只比较末时刻图像；c<5 因运行时间长被排除且未正式优化 c。",
    "【原文限制】Fig 7/8 是相对排名，不代表绝对拟合良好；Model 4 的规则修改超出本文范围。",
    "【作者解释】框架可泛化到任何具备时空分辨数据的建模比较；本文仅在气–水–均质砂体系实证，属推广性论断。",
    "【汇报组织关系】本汇报按科研任务而非 Figure 编号重排；分支、汇合与共享证据均来自已审核的 Research Logic，"
    "未为复杂而虚构分叉。",
]
FOUR = [
    "背景缺口：IP 模型传统上只用于毛管主导的不连续气流区；跨三流区的系统互比仍缺。",
    "核心问题：这些宏观 IP 模型能否描述连续、过渡态气流？",
    "研究问题：若不能，哪种模型最合适？",
    "研究问题：从成功与不成功的策略比较中能获得哪些改进建议？",
]


def build(tmp, bullets):
    d = Path(tmp)
    data = {"figure_assets": "", "slides": [{
        "kind": "question", "title": "独立支线与证据边界：哪些内容不属于主比较网络的结论？",
        "lead": "这一页把『论文原始发现』『作者解释』『Agent 建模判断』与『汇报组织关系』分开陈述。",
        "bullets": bullets}]}
    j = d / "s.json"
    j.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    t = d / "t.pptx"
    o = d / "o.pptx"
    bp.make_default_template(t)
    bp.build(j, o, t, "auto", False, False)
    return Presentation(str(o)).slides[0]


def geom(sl):
    card = next(s for s in sl.shapes if s.name == "DECOR_card")
    box = next(s for s in sl.shapes if s.name == "PFS_BULLETS")
    size = box.text_frame.paragraphs[0].runs[0].font.size.pt
    return (card.top / EMU, (card.top + card.height) / EMU,
            box.top / EMU, (box.top + box.height) / EMU, size,
            box.text_frame.auto_size)


class QuestionCardFit(unittest.TestCase):
    def test_six_bullets_stay_inside_card_and_clear_footer(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_top, card_bottom, box_top, box_bottom, size, auto = geom(build(tmp, SIX))
            self.assertLessEqual(box_bottom, card_bottom - .10,
                                 "bullets extend past the card")
            self.assertLessEqual(card_bottom, bp.CARD_MAX_BOTTOM + 1e-6,
                                 "card encroaches on the footer rule")
            self.assertGreaterEqual(size, 15, "font shrank below readable size")
            self.assertEqual(auto, MSO_AUTO_SIZE.NONE,
                             "auto-grow must be disabled so hosts cannot re-flow")

    def test_four_bullets_keep_standard_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            card_top, card_bottom, box_top, box_bottom, size, auto = geom(build(tmp, FOUR))
            self.assertAlmostEqual(card_bottom, 6.81, places=2,
                                   msg="light pages must not change card height")
            self.assertEqual(size, 21.0)
            self.assertLessEqual(box_bottom, card_bottom)

    def test_fit_bullets_prefers_largest_fitting_size(self):
        size, need = bp.fit_bullets(SIX, 11.0, 3.42, 21)
        self.assertLessEqual(need, 3.42 * .97 + 1e-9)
        self.assertGreaterEqual(size, 15)


if __name__ == "__main__":
    unittest.main()
