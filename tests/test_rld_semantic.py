"""RLD v1.2 候选自包含测试：语义层 + 诊断器 + 数值门禁。

不依赖本机任何历史目录；只依赖本包 scripts/ 与 examples/minimal_rld/。
运行：python -m unittest discover -s tests -p "test_rld_*.py"
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rld_semantic as sem   # noqa: E402
import rld_diagnose as rld   # noqa: E402

EX = ROOT / "examples" / "minimal_rld"


def T(text):
    return sem.classify_text(text)


class Language(unittest.TestCase):
    """中/英/混合/否定/假说/相关负对照。"""

    def test_en_causal(self):
        self.assertEqual("CAUSAL_ASSERTION", T("Compound X promotes readout Y.")["dominant"])

    def test_zh_causal(self):
        self.assertEqual("CAUSAL_ASSERTION", T("化合物 X 促进读出 Y。")["dominant"])

    def test_mixed_causal(self):
        self.assertEqual("CAUSAL_ASSERTION", T("化合物 X 促进 readout Y.")["dominant"])

    def test_en_negation(self):
        r = T("Compound X did not promote readout Y.")
        self.assertEqual("NEGATED_CAUSAL", r["dominant"])
        self.assertFalse(r["asserted"])

    def test_zh_negation(self):
        r = T("化合物 X 并未促进读出 Y。")
        self.assertEqual("NEGATED_CAUSAL", r["dominant"])
        self.assertFalse(r["asserted"])

    def test_negated_existential(self):
        self.assertEqual("NEGATED_CAUSAL",
                         T("There is no evidence that X promotes Y.")["dominant"])

    def test_en_hypothesis(self):
        self.assertEqual("CAUSAL_HYPOTHESIS",
                         T("We tested whether X may promote Y.")["dominant"])

    def test_zh_hypothesis(self):
        self.assertEqual("CAUSAL_HYPOTHESIS", T("本研究旨在检验 X 是否促进 Y。")["dominant"])

    def test_correlation_negative_control(self):
        self.assertEqual("CORRELATION_ONLY", T("Y was associated with X.")["dominant"])
        self.assertEqual("CORRELATION_ONLY", T("Y 与 X 呈正相关。")["dominant"])

    def test_uncertain(self):
        self.assertEqual("UNCERTAIN", T("结果提示 X 可能参与 Y。")["dominant"])

    def test_descriptive_regulation(self):
        self.assertEqual("DESCRIPTIVE_REGULATION", T("These genes were actively regulated.")["dominant"])
        self.assertEqual("DESCRIPTIVE_REGULATION", T("这些基因受严格调控。")["dominant"])

    def test_active_agent_is_assertion(self):
        self.assertEqual("CAUSAL_ASSERTION", T("X regulates Y signalling.")["dominant"])

    def test_noun_form_is_not_causal(self):
        self.assertEqual("NO_CAUSAL_CONTENT", T("counts with downregulation dominant")["dominant"])

    def test_hyphenated_compound_is_not_causal(self):
        self.assertEqual("NO_CAUSAL_CONTENT",
                         T("uptake via clathrin-mediated endocytosis")["dominant"])


class Scope(unittest.TestCase):
    def test_negation_other_clause(self):
        self.assertTrue(T("X promotes Y, but Z was not changed.")["asserted"])

    def test_not_only(self):
        self.assertTrue(T("X not only promotes Y but also reduces Z.")["asserted"])
        self.assertTrue(T("X 不仅促进 Y，也改善 Z。")["asserted"])

    def test_chinese_compound_bu(self):
        self.assertTrue(T("不同剂量的 X 促进 Y。")["asserted"])

    def test_may_not(self):
        self.assertEqual("NEGATED_CAUSAL", T("X may not promote Y.")["dominant"])


class NeverSilent(unittest.TestCase):
    def test_uncovered_script(self):
        r = T("クラステリンは心臓を守る。")
        self.assertEqual("UNASSESSED_LANGUAGE", r["dominant"])
        self.assertFalse(r["coverage"]["assessable"])

    def test_empty(self):
        self.assertEqual("UNASSESSED_LANGUAGE", T("")["dominant"])

    def test_plain_is_assessed(self):
        r = T("Y was measured at day 28.")
        self.assertEqual("NO_CAUSAL_CONTENT", r["dominant"])
        self.assertTrue(r["coverage"]["assessable"])

    def test_vocab_declared(self):
        self.assertEqual("rld-semantic-vocab-1", sem.VOCAB_VERSION)


class ExampleDiagnosis(unittest.TestCase):
    """用包自带最小示例验证四类结果。"""

    @classmethod
    def setUpClass(cls):
        cls.res = rld.diagnose(json.loads((EX / "network.json").read_text(encoding="utf-8")),
                               json.loads((EX / "research_logic.json").read_text(encoding="utf-8")),
                               json.loads((EX / "argument_units.json").read_text(encoding="utf-8")))

    def test_supported_causal_is_not_reported(self):
        self.assertEqual("ASSERTED_WITH_REGISTERED_INTERVENTION_SUPPORT",
                         self.res["causal_disposition"]["AU_CL_SUP"])
        self.assertNotIn("AU_CL_SUP", {f["unit_id"] for f in self.res["findings"]})

    def test_orphan_causal_is_reported_to_reconstruction(self):
        f = [x for x in self.res["findings"] if x["unit_id"] == "AU_CL_ORPHAN"]
        self.assertEqual(1, len(f))
        self.assertEqual("CAUSAL_UPGRADE", f[0]["check"])
        self.assertEqual("PFS_RECONSTRUCTION", f[0]["attribution"])
        self.assertTrue(f[0]["reversible"])
        self.assertTrue(f[0]["what_would_change"])

    def test_correlation_is_not_reported_as_causal(self):
        self.assertEqual("NOT_ASSERTED:CORRELATION_ONLY", self.res["causal_disposition"]["AU_CL_CORR"])

    def test_unassessed_is_reported_not_silent(self):
        cov = [x for x in self.res["findings"] if x["check"] == "SEMANTIC_TYPE_UNRECOGNIZED"]
        self.assertEqual(1, len(cov))
        self.assertEqual("RLD_COVERAGE_GAP", cov[0]["attribution"])
        self.assertEqual(1, self.res["coverage"]["unassessed"])
        self.assertNotIn("AU_CL_FOREIGN", self.res["no_issue_units"])

    def test_boundary_fields(self):
        self.assertEqual("NOT_ESTIMABLE", self.res["boundary"]["scientific_accuracy"])
        self.assertFalse(self.res["boundary"]["pfs_modified"])


if __name__ == "__main__":
    unittest.main()
