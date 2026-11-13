#!/usr/bin/env python3
"""PFS → RLD 论证单元交接（真实工件派生，非预制）。

输入：Scientific Index + Evidence Network + Research Logic（三者均由正式 PFS 生成并校验通过）。
输出：`rld_argument_units_v1`，可直接喂给 `rld_diagnose.py`。

铁律
----
1. **只用 PFS 已登记的文本**。claim 必须来自 role=interpretation 的 statement；
   绝不把逻辑节点 label 当作论文主张（label 是 Agent 撰写的注解，不是来源）。
2. 每个字段都带 `status` 与 `source`（statement id / logic edge id / null）。
3. 三态不混：EXPLICIT_IN_PFS（逐字来自 statement）/ AGENT_RECONSTRUCTED_CANDIDATE
   （来自逻辑边的 rationale）/ INSUFFICIENT_GRAPH_INFORMATION（PFS 没这个字段）。
4. 保留 PDF 身份：每个 source_ref 带 document_id 与 document_sha256；
   顶层记录 index 的 file_sha256，并对不一致显式报错。
5. 不推断因果：本模块只搬运与标注，不做任何语义判断。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VERSION = "rld_argument_units_v1"
DERIVATION = "rld-units-from-pfs-1"

EXPLICIT = "EXPLICIT_IN_PFS"
AGENT = "AGENT_RECONSTRUCTED_CANDIDATE"
MISSING = "INSUFFICIENT_GRAPH_INFORMATION"

# 哪些 statement role 可以充当论证单元的哪个字段
ROLE_FIELD = {
    "purpose": "question",
    "design": "design",
    "method": "design",
    "readout": "design",
    "result": "observations",
    "interpretation": "claim",
    "limitation": "limits",
}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validated_inputs(index_path, network_path, logic_path):
    from scientific_index import validate as validate_index
    from evidence_network import validate_network
    from research_logic import validate_model

    index, network, logic = map(load, (index_path, network_path, logic_path))
    if logic.get("network_snapshot") != network.get("snapshot"):
        raise ValueError("NETWORK_SNAPSHOT_MISMATCH")
    for key, path in (("scientific_index", index_path), ("network", network_path)):
        if logic.get("inputs", {}).get(key, {}).get("sha256") != sha(path):
            raise ValueError("PFS_INPUT_SHA_MISMATCH: " + key)
    if not index.get("file_sha256") or not any(
        d.get("sha256") == index["file_sha256"] for d in network["paper"]["documents"]
    ):
        raise ValueError("PDF_IDENTITY_MISMATCH")
    for name, check, obj in (
        ("index", validate_index, index), ("network", validate_network, network),
        ("logic", validate_model, logic),
    ):
        receipt = check(obj)
        if not receipt["valid"]:
            raise ValueError(name + ": " + json.dumps(receipt["errors"], ensure_ascii=False))
    return index, network, logic


def _ref_key(r):
    loc = r.get("locator") or {}
    return (r.get("document_id"), loc.get("physical_page"), loc.get("section"))


def _unit_kind(node, roles):
    """沿用 R1.15 的单元类型判定，只依据身份与角色，不看标签语义。"""
    label = (node.get("label") or "").lower()
    if "protocol" in label or "sampling" in label or "pipeline" in label:
        return "EXPERIMENTAL_DESIGN"
    if node.get("identity") == "AUTHOR_INTERPRETATION":
        return "SCIENTIFIC_INTERPRETATION"
    if "result" in roles:
        return "NUMERIC_COMPARISON"
    return "SCIENTIFIC_INTERPRETATION"


def build(index, network, logic):
    stmts = {s["id"]: s for s in network.get("statements", [])}
    docs = {d["id"]: d for d in (network.get("paper") or {}).get("documents", [])}
    logic_nodes = {n["id"]: n for n in logic.get("nodes", [])}
    logic_edges = logic.get("edges", [])

    index_pdf_sha = index.get("file_sha256")
    doc_sha_mismatch = []
    for did, d in docs.items():
        ds = d.get("sha256")
        if ds and index_pdf_sha and d.get("role") == "main_paper" and ds != index_pdf_sha:
            doc_sha_mismatch.append({"document_id": did, "network_sha256": ds,
                                     "index_file_sha256": index_pdf_sha})
    if doc_sha_mismatch:
        raise SystemExit("PDF_IDENTITY_MISMATCH: " + json.dumps(doc_sha_mismatch, ensure_ascii=False))

    units, unlabelled = [], []
    for node in logic.get("nodes", []):
        sids = node.get("statement_ids", [])
        if any(sid not in stmts for sid in sids):
            raise ValueError("UNKNOWN_STATEMENT: " + node["id"])
        by_field = {}
        for sid in sids:
            field = ROLE_FIELD.get(stmts[sid].get("role"))
            if field:
                by_field.setdefault(field, []).append(sid)

        def value(field):
            ids = by_field.get(field, [])
            return [stmts[i]["text"] for i in ids], ids

        q_txt, q_ids = value("question")
        d_txt, d_ids = value("design")
        o_txt, o_ids = value("observations")
        c_txt, c_ids = value("claim")
        l_txt, l_ids = value("limits")

        refs, seen = [], set()
        for sid in sids:
            for r in stmts[sid].get("source_refs", []):
                k = _ref_key(r)
                if k in seen:
                    continue
                seen.add(k)
                did = r.get("document_id")
                refs.append({"document_id": did,
                             "physical_page": (r.get("locator") or {}).get("physical_page"),
                             "section": (r.get("locator") or {}).get("section"),
                             "verification": r.get("verification", "pending"),
                             "document_sha256": (docs.get(did) or {}).get("sha256"),
                             "locator": r.get("locator"),
                             "from_statement": sid})

        premises = [{"edge_id": e["id"], "from": e.get("from"), "type": e.get("type"),
                     "rationale": e.get("rationale"), "origin": "logic_edge_rationale"}
                    for e in logic_edges if e.get("to") == node["id"]]

        claim_value = c_txt[0] if c_txt else None
        unit = {
            "unit_id": "AU_" + node["id"],
            "kind": _unit_kind(node, {stmts[s].get("role") for s in sids}),
            "pfs_anchors": {
                "logic_node_id": node["id"],
                "statement_ids": sids,
                "logic_edge_ids": [e["id"] for e in logic_edges if e.get("to") == node["id"]],
                "entity_ids": node.get("source_entity_ids", []),
            },
            "source_refs": refs,
            "question": {"value": q_txt[0] if q_txt else None,
                         "status": EXPLICIT if q_txt else MISSING,
                         "source_statement_ids": q_ids},
            "design": {"statements": d_txt, "status": EXPLICIT if d_txt else MISSING,
                       "source_statement_ids": d_ids},
            "observations": {"statements": o_txt, "status": EXPLICIT if o_txt else MISSING,
                             "source_statement_ids": o_ids},
            # claim 绝不用 label 兜底：没有 interpretation 语句就是信息不足
            "claim": {"value": claim_value,
                      "status": EXPLICIT if claim_value else MISSING,
                      "source_statement_ids": c_ids,
                      "label_not_used_as_claim": True},
            "premises": {"value": premises,
                         "status": AGENT if premises else MISSING},
            "comparison_conditions": {"value": None, "status": MISSING,
                                      "note": "PFS statement 层不携带对照/基准字段；"
                                              "如需比较基准请用 rld_numeric 的主张规格"},
            "limits": {"value": l_txt, "status": EXPLICIT if l_txt else MISSING,
                       "source_statement_ids": l_ids},
            "derivation": {
                "mode": DERIVATION,
                "logic_identity": node.get("identity"),
                "statement_count": len(sids),
                "declared_fields": sorted(by_field),
                "missing_fields": [f for f in ("question", "design", "observations", "claim", "limits")
                                   if not by_field.get(f)],
            },
            "usable_for_causal_check": bool(claim_value),
        }
        if not claim_value:
            unlabelled.append(node["id"])
        units.append(unit)

    return {
        "schema": VERSION,
        "derivation": DERIVATION,
        "note": ("论证单元由正式 PFS 三件工件派生；claim 仅取自 role=interpretation 的登记语句，"
                 "不使用逻辑节点 label。label 缺失不影响提取，但会导致该单元无主张可判。"),
        "identity": {
            "index_file_sha256": index_pdf_sha,
            "index_reading_status": index.get("reading_status"),
            "network_snapshot": network.get("snapshot"),
            "logic_snapshot": logic.get("snapshot"),
            "documents": [{"document_id": d["id"], "sha256": d.get("sha256"),
                           "physical_page_count": d.get("physical_page_count")}
                          for d in docs.values()],
        },
        "counts": {"logic_nodes": len(logic_nodes), "units": len(units),
                   "units_with_claim": sum(1 for u in units if u["usable_for_causal_check"]),
                   "units_without_claim_statement": len(unlabelled)},
        "units": units,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Derive RLD argument units from real PFS artifacts.")
    ap.add_argument("--index", required=True, type=Path)
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--logic", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    try:
        doc = build(*validated_inputs(a.index, a.network, a.logic))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        ap.error(str(exc))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"units": doc["counts"]["units"],
                      "with_claim": doc["counts"]["units_with_claim"],
                      "without_claim": doc["counts"]["units_without_claim_statement"],
                      "network_snapshot": doc["identity"]["network_snapshot"],
                      "logic_snapshot": doc["identity"]["logic_snapshot"],
                      "pdf_sha256": doc["identity"]["index_file_sha256"],
                      "out": str(a.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
