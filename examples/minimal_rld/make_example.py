#!/usr/bin/env python3
"""生成 examples/minimal_rld 的最小合法输入（全合成，不含任何真实论文内容）。

用途：让使用者在不接触任何真实论文数据的情况下跑通一次 RLD 诊断，
并看到四类结果：已支持（不报）/ 断言无干预支持（报）/ 仅相关（不报）/ 未覆盖语言（上报）。
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)


def w(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---- 合成 M1 网络：化合物 X vs 溶剂对照，读出 Y ----
net = {
    "version": "pfs-evidence-network-1",
    "snapshot": "synthetic-example-snapshot-not-a-real-model",
    "paper": {"id": "synthetic_demo", "paper_type": "original_research", "title": "Synthetic demo paper",
              "documents": [{"id": "synthetic_demo", "role": "main_paper", "format": "pdf",
                             "title": "Synthetic demo paper", "version": "demo",
                             "availability": "available", "sha256": None,
                             "hash_status": "unavailable", "source_locator": "demo",
                             "physical_page_count": 1}]},
    "nodes": [
        {"id": "IV_X", "kind": "intervention", "label": "compound X"},
        {"id": "IV_VEH", "kind": "intervention", "label": "vehicle"},
        {"id": "EV_Y", "kind": "evidence", "label": "readout Y"},
        {"id": "CL_SUP", "kind": "claim", "label": "X improves Y"},
        {"id": "CL_OBS", "kind": "claim", "label": "Y correlates with X"},
        {"id": "CL_FOREIGN", "kind": "claim", "label": "X improves Y (uncovered language)"},
    ],
    "edges": [
        {"id": "E_CMP", "type": "compares", "from": "IV_X", "to": "IV_VEH", "certainty": "paper_reported"},
        {"id": "E_DATA", "type": "data_depends_on", "from": "IV_X", "to": "EV_Y", "certainty": "paper_reported"},
        {"id": "E_SUP", "type": "evidence_supports", "from": "EV_Y", "to": "CL_SUP", "certainty": "paper_reported"},
    ],
    "statements": [
        {"id": "S_NAME", "role": "design", "text": "compound X versus vehicle", "source_refs": []},
        {"id": "S_OBS", "role": "result", "text": "readout Y increased", "source_refs": []},
        {"id": "S_CLM", "role": "interpretation", "text": "Compound X promotes readout Y.",
         "source_refs": []},
        {"id": "S_LIM", "role": "limitation", "text": "single synthetic demo, no real data",
         "source_refs": []},
        {"id": "S_CORR", "role": "interpretation",
         "text": "Readout Y is associated with compound X.", "source_refs": []},
    ],
}

# ---- 合成 research logic ----
logic = {
    "version": "pfs-research-logic-1",
    "snapshot": "synthetic-example-logic-snapshot",
    "network_snapshot": net["snapshot"],
    "nodes": [
        {"id": "LN_Q", "identity": "AUTHOR_ARGUMENT", "label": "does X change Y",
         "statement_ids": ["S_NAME"], "source_entity_ids": ["IV_X"]},
        {"id": "LN_EV", "identity": "SCIENTIFIC_EVIDENCE", "label": "Y measurement",
         "statement_ids": ["S_OBS"], "source_entity_ids": ["EV_Y"]},
        {"id": "LN_CL", "identity": "AUTHOR_INTERPRETATION", "label": "X promotes Y",
         "statement_ids": ["S_CLM", "S_LIM"], "source_entity_ids": ["CL_SUP"]},
        {"id": "LN_OB", "identity": "AUTHOR_ARGUMENT", "label": "correlation only",
         "statement_ids": ["S_CLM"], "source_entity_ids": ["CL_OBS"]},
        {"id": "LN_FO", "identity": "AUTHOR_ARGUMENT", "label": "uncovered script",
         "statement_ids": ["S_CLM"], "source_entity_ids": ["CL_FOREIGN"]},
    ],
    "edges": [
        {"id": "LE_1", "from": "LN_Q", "to": "LN_EV", "type": "progression",
         "identity": "AUTHOR_ARGUMENT", "rationale": "question then measurement",
         "alternatives": ["parallel"], "source_ids": []},
        {"id": "LE_2", "from": "LN_EV", "to": "LN_CL", "type": "evidence_convergence",
         "identity": "SCIENTIFIC_EVIDENCE", "rationale": "measurement supports claim",
         "alternatives": ["association only"], "source_ids": []},
    ],
}


def unit(uid, node, kind, claim, obs, limit, entity_ids, cmp_status="INSUFFICIENT_GRAPH_INFORMATION",
         q=None, design=None, stmts=None):
    return {
        "unit_id": uid, "kind": kind,
        "pfs_anchors": {"logic_node_id": node, "statement_ids": stmts or ["S_CLM"],
                        "logic_edge_ids": [], "entity_ids": entity_ids},
        "source_refs": [{"document_id": "synthetic_demo", "physical_page": 1}],
        "question": ({"value": q, "status": "EXPLICIT_IN_PFS"} if q
                     else {"value": None, "status": "INSUFFICIENT_GRAPH_INFORMATION"}),
        "design": ({"statements": [design], "status": "EXPLICIT_IN_PFS"} if design
                   else {"statements": [], "status": "INSUFFICIENT_GRAPH_INFORMATION"}),
        "observations": {"statements": obs, "status": "EXPLICIT_IN_PFS"},
        "claim": {"value": claim, "status": "EXPLICIT_IN_PFS"},
        "premises": {"value": [], "status": "AGENT_RECONSTRUCTED_CANDIDATE"},
        "comparison_conditions": {"value": None, "status": cmp_status},
        "limits": {"value": limit, "status": "EXPLICIT_IN_PFS" if limit else "INSUFFICIENT_GRAPH_INFORMATION"},
    }


units = {"schema": "rld_argument_units_v1", "units": [
    # 1) 断言因果，但网络里有干预+对照+读出连线 -> 应判 SUPPORTED，不报
    unit("AU_CL_SUP", "LN_CL", "SCIENTIFIC_INTERPRETATION",
         "Compound X promotes readout Y.", ["readout Y increased"], ["single synthetic demo"], ["EV_Y"]),
    # 2) 断言因果，但证据够不到任何干预 -> 应报（归重建缺口，因为模型里确有干预）
    unit("AU_CL_ORPHAN", "LN_OB", "SCIENTIFIC_INTERPRETATION",
         "Compound X drives readout Y.", ["readout Y increased"], ["none"], ["CL_OBS"],
         q="does X drive Y", design="compound X treatment only"),
    # 3) 仅相关 -> 不应报
    unit("AU_CL_CORR", "LN_OB", "SCIENTIFIC_INTERPRETATION",
         "Readout Y is associated with compound X.", ["readout Y increased"], ["none"], ["CL_OBS"],
         q="is Y associated with X", design="observational sampling", stmts=["S_CORR"]),
    # 4) 未覆盖语言 -> 应上报覆盖缺口，而不是静默 0
    unit("AU_CL_FOREIGN", "LN_FO", "SCIENTIFIC_INTERPRETATION",
         "クラステリンは心臓を守る。", [], ["none"], ["CL_FOREIGN"],
         q="uncovered script demo", design="not applicable"),
]}

if __name__ == "__main__":
    w("network.json", net)
    w("research_logic.json", logic)
    w("argument_units.json", units)
    print("written:", sorted(p.name for p in OUT.glob("*.json")))
